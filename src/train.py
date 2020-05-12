import time
import torch.nn.functional as F
from torchvision.utils import save_image
import wandb
from tqdm import tqdm, trange

from wt_utils import *

# Train function for UNet 128 (64->128) without data augmentation
def train_unet128(epoch, state_dict, model, optimizer, dataloader, args, logger):
    model.train()

    filters = create_filters(device=args.device)
    inv_filters = create_inv_filters(device=args.device)

    for i, data in tqdm(dataloader):
        start_time = time.time()
        optimizer.zero_grad()

        data = data.to(args.device)
    
        Y = wt_128_3quads(data, filters, levels=3)

        # Get real 1st level masks
        Y_64 = Y[:, :, :64, :64]
        real_mask_64_tl, real_mask_64_tr, real_mask_64_bl, real_mask_64_br = get_4masks(Y_64, 32)
        Y_64_patches = torch.cat((real_mask_64_tl, real_mask_64_tr, real_mask_64_bl, real_mask_64_br), dim=1)

        # Get real 2nd level masks
        real_mask_tr, real_mask_bl, real_mask_br = get_3masks(Y, args.mask_dim)

        # Divide into 32 x 32 patches
        real_mask_tr_patches = create_patches_from_grid(real_mask_tr)
        real_mask_bl_patches = create_patches_from_grid(real_mask_bl)
        real_mask_br_patches = create_patches_from_grid(real_mask_br)

        # Run through 128 mask network and get reconstructed image
        recon_mask_all = model(Y_64_patches)
        recon_mask_tr, recon_mask_bl, recon_mask_br = split_masks_from_channels(recon_mask_all)
    
        # Reshape channel-wise concatenated patches to new dimension
        recon_mask_tr_patches = recon_mask_tr.reshape(recon_mask_tr.shape[0], -1, 3, 32, 32)
        recon_mask_bl_patches = recon_mask_bl.reshape(recon_mask_bl.shape[0], -1, 3, 32, 32)
        recon_mask_br_patches = recon_mask_br.reshape(recon_mask_br.shape[0], -1, 3, 32, 32)
        
        # Calculate loss
        loss = 0
        for j in range(real_mask_tr_patches.shape[1]):
            loss += F.mse_loss(real_mask_tr_patches[:,j], recon_mask_tr_patches[:,j])
            loss += F.mse_loss(real_mask_bl_patches[:,j], recon_mask_bl_patches[:,j])
            loss += F.mse_loss(real_mask_br_patches[:,j], recon_mask_br_patches[:,j])
            
        loss.backward()
        optimizer.step()
        
        # Calculate iteration time
        end_time = time.time()
        itr_time = end_time - start_time

        # Update logger & wandb
        logger.update(state_dict['itr'], loss.item(), itr_time)
        wandb.log({'train_loss': loss.item()}, commit=False)
        wandb.log({'train_itr_time': itr_time}, commit=False)    

        # Save images, logger, weights on save_every interval
        if not state_dict['itr'] % args.save_every:
            Y_real = wt(data, filters, levels=3)
            zeros = torch.zeros(real_mask_tr.shape)

            # Real mask -- in 32x32 patches
            real_mask = collate_patches_to_img(zeros, real_mask_tr, real_mask_bl, real_mask_br)
            
            # Real mask -- IWT'ed
            real_mask_tr_iwt = iwt(real_mask_tr, inv_filters, levels=1)
            real_mask_bl_iwt = iwt(real_mask_bl, inv_filters, levels=1)
            real_mask_br_iwt = iwt(real_mask_br, inv_filters, levels=1)
            real_mask_iwt = collate_patches_to_img(zeros, real_mask_tr_iwt, real_mask_bl_iwt, real_mask_br_iwt)
            
            real_img_128_padded = Y_real[:, :, :128, :128]
            real_img_128_padded = zero_pad(real_img_128_padded, 256, args.device)
            real_img_128_padded = iwt(real_img_128_padded, inv_filters, levels=3)

            # Collate all masks concatenated by channel to an image (slice up and put into a square)
            recon_mask_tr_img = collate_channels_to_img(recon_mask_tr, args.device)
            recon_mask_bl_img = collate_channels_to_img(recon_mask_bl, args.device)   
            recon_mask_br_img = collate_channels_to_img(recon_mask_br, args.device)

            recon_mask = collate_patches_to_img(zeros, recon_mask_tr_img, recon_mask_bl_img, recon_mask_br_img)
            
            recon_mask_tr_img = iwt(recon_mask_tr_img, inv_filters, levels=1)
            recon_mask_bl_img = iwt(recon_mask_bl_img, inv_filters, levels=1)    
            recon_mask_br_img = iwt(recon_mask_br_img, inv_filters, levels=1) 
            
            recon_mask_iwt = collate_patches_to_img(zeros, recon_mask_tr_img, recon_mask_bl_img, recon_mask_br_img)
            
            recon_mask_padded = zero_pad(recon_mask_iwt, 256, args.device)
            recon_mask_padded[:, :, :64, :64] = Y_64
            recon_img = iwt(recon_mask_padded, inv_filters, levels=3)
            
            # Reconstructed image with only 64x64
            Y_64_low = zero_pad(Y_64, 256, args.device)
            Y_64_low = iwt(Y_64_low, inv_filters, levels=3)
            
            # Save images
            save_image(real_mask.cpu(), args.output_dir + 'real_mask_itr{}.png'.format(state_dict['itr']))
            save_image(real_mask_iwt.cpu(), args.output_dir + 'real_mask_iwt_itr{}.png'.format(state_dict['itr']))
            
            save_image(recon_mask.cpu(), args.output_dir + 'recon_mask_itr{}.png'.format(state_dict['itr']))
            save_image(recon_mask_iwt.cpu(), args.output_dir + 'recon_mask_iwt_itr{}.png'.format(state_dict['itr']))
            
            save_image(recon_img.cpu(), args.output_dir + 'recon_img_itr{}.png'.format(state_dict['itr']))
            save_image(Y_64_low.cpu(), args.output_dir + 'low_img_64_full_itr{}.png'.format(state_dict['itr']))

            save_image(real_img_128_padded.cpu(), args.output_dir + 'img_128_real_masks_itr{}.png'.format(state_dict['itr']))
            save_image(data.cpu(), args.output_dir + 'img_itr{}.png'.format(state_dict['itr']))
            
            # Save model & optimizer weights
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                }, args.output_dir + '/iwt_model_128_itr{}.pth'.format(state_dict['itr']))
            
            # Save logger 
            torch.save(logger, args.output_dir + '/logger.pth')

        # Increment iteration number
        state_dict['itr'] += 1       