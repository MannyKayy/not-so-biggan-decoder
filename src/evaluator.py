import torch
from torchvision.utils import save_image
from utils.utils import zero_mask, save_plot

def eval_ae_mask(epoch, wt_model, model, sample_loader, args, img_output_dir, model_dir, writer):
    with torch.no_grad():
        model.eval()
        
        for data in sample_loader:
            data = data.to(model.device)
            
            # Get Y
            Y = wt_model(data)
            
            # Zeroing out first patch
            Y = zero_mask(Y, num_iwt=args.num_wt, cur_iwt=1)

            x_hat = model(Y.to(model.device))

            save_image(x_hat.cpu(), img_output_dir + '/sample_recon{}.png'.format(epoch))
            save_image(Y.cpu(), img_output_dir + '/sample{}.png'.format(epoch))

    torch.save(model.state_dict(), model_dir + '/aemask512_epoch{}.pth'.format(epoch))
