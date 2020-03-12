import os, sys
import torch
from torch import optim
from torch.utils.data import DataLoader, Subset
from torchvision.utils import save_image
import numpy as np
from vae_models import WTVAE_64, IWTVAE_64, IWTVAE_64_Mask, IWTVAE_64_Bottleneck, IWTVAE_64_FreezeIWT
from wt_datasets import CelebaDataset
from trainer import train_iwtvae
from arguments import args_parse
from utils.utils import zero_patches, set_seed, save_plot
import matplotlib.pyplot as plt
import logging
import pywt
from random import sample


if __name__ == "__main__":
    # Accelerate training since fixed input sizes
    torch.backends.cudnn.benchmark = True 

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(message)s')
    LOGGER = logging.getLogger(__name__)

    args = args_parse()

    # Set seed
    set_seed(args.seed)

    dataset_dir = os.path.join(args.root_dir, 'celeba64')
    train_dataset = CelebaDataset(dataset_dir, os.listdir(dataset_dir), WT=False)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, num_workers=10, shuffle=True)
    sample_dataset = Subset(train_dataset, sample(range(len(train_dataset)), 8))
    sample_loader = DataLoader(sample_dataset, batch_size=8, shuffle=False) 
    
    if torch.cuda.is_available() and torch.cuda.device_count() >= 2:
        devices = ['cuda:0', 'cuda:1']
    else: 
        devices = ['cpu', 'cpu']

    if args.mask:
        iwt_model = IWTVAE_512_Mask()
    
    if args.zero:
        LOGGER.info('Zero-ing out all patches other than 1st')

    iwt_model = iwt_model.to(devices[0])
    iwt_model.set_devices(devices)
    
    train_losses = []
    optimizer = optim.Adam(iwt_model.parameters(), lr=args.lr)

    img_output_dir = os.path.join(args.root_dir, 'image_samples/iwtvae64_{}'.format(args.config))
    model_dir = os.path.join(args.root_dir, 'models/iwtvae64_{}/'.format(args.config))

    try:
        os.mkdir(img_output_dir)
        os.mkdir(model_dir)
    except:
        LOGGER.error('Could not make model & img output directories')
        raise Exception('Could not make model & img output directories')
    
    for epoch in range(1, args.epochs + 1):
        train_iwtvae(epoch, wt_model, iwt_model, optimizer, train_loader, train_losses, args)
        
        with torch.no_grad():
            iwt_model.eval()
            
            for data in sample_loader:
                data0 = data.to(devices[0])
                data1 = data.to(devices[1])
                
                z_sample = torch.randn(data.shape[0],100).to(devices[0])
                
                Y = wt_model(data1)[0]
                if args.zero:
                    Y = zero_patches(Y)
                Y = Y.to(devices[0])
    
                mu, var = iwt_model.encode(data0, Y)
                x_hat = iwt_model.decode(Y, mu)
                x_sample = iwt_model.decode(Y, z_sample)

                save_image(x_hat.cpu(), img_output_dir + '/sample_recon{}.png'.format(epoch))
                save_image(x_sample.cpu(), img_output_dir + '/sample_z{}.png'.format(epoch))
                save_image(Y.cpu(), img_output_dir + '/sample_y{}.png'.format(epoch))
                save_image(data.cpu(), img_output_dir + '/sample{}.png'.format(epoch))
    
        torch.save(iwt_model.state_dict(), model_dir + '/iwtvae_epoch{}.pth'.format(epoch))
    
    # Save train losses and plot
    np.save(model_dir+'/train_losses.npy', train_losses)
    save_plot(train_losses, img_output_dir + '/train_loss.png')
    
    LOGGER.info('IWT Model parameters: {}'.format(sum(x.numel() for x in iwt_model.parameters())))

    
    
    