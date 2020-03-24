import os, sys
import torch
import numpy as np
from utils.utils import zero_patches, calc_grad_norm_2
import logging

log_idx = 0
decoder_outputs = []
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(message)s')

def get_decoder_output(self, input, output):
    global decoder_outputs
    decoder_outputs.append(output)

def train_wtvae(epoch, model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    model.train()
    train_loss = 0

    for batch_idx, data in enumerate(train_loader):
        
        if model.cuda:
            data = data.to(model.device)

        optimizer.zero_grad()
        
        wt_data, mu, logvar = model(data)
        loss, loss_bce, loss_kld = model.loss_function(data, wt_data, mu, logvar, kl_weight=args.kl_weight)
        loss.backward()

        # Calculating and printing gradient norm
        total_norm = calc_grad_norm_2(model)

        global log_idx
        writer.add_scalar('Loss/total', loss, log_idx)
        writer.add_scalar('Loss/bce', loss_bce, log_idx)
        writer.add_scalar('Loss/kld', loss_kld, log_idx)
        writer.add_scalar('Gradient_norm/before', total_norm, log_idx)
        writer.add_scalar('KL_weight', args.kl_weight, log_idx)
        log_idx += 1 

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip, norm_type=2)
            
            # Re-calculating and printing gradient norm
            total_norm = calc_grad_norm_2(model)
            writer.add_scalar('Gradient_norm/clipped', total_norm, log_idx)

        train_losses.append((loss.item(), loss_bce, loss_kld))
        train_loss += loss
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
                                                                            len(train_loader.dataset),
                                                                            100. * batch_idx / len(train_loader),
                                                                            loss / len(data)))
            
            n = min(data.size(0), 8)
            
    writer.flush()
    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))

def train_wtvae_128(epoch, model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    model.train()
    train_loss = 0
    anneal_rate = (1.0 - args.kl_start) / (args.kl_warmup * len(train_loader))
    global decoder_outputs

    # Register hook onto decoder so that we can compute additional loss on reconstruction of original image (in adddition to patch loss)
    model.decoder.register_forward_hook(get_decoder_output)

    for batch_idx, data in enumerate(train_loader):
        args.kl_weight = min(1.0, args.kl_weight + anneal_rate)
        data128 = data[0]
        data512 = data[1]
        if model.cuda:
            data128 = data128.to(model.device)
            data512 = data512.to(model.device)

        optimizer.zero_grad()
        
        wt_data, mu, logvar = model(data128)
        decoder_output = decoder_outputs[-1]
        loss, loss_bce, loss_kld = model.loss_function(data512, data128, wt_data, decoder_output, mu, logvar, kl_weight=args.kl_weight)
        loss.backward()
        
        # Clearing saved outputs
        decoder_outputs.clear()

        # Calculating and printing gradient norm
        total_norm = calc_grad_norm_2(model)

        global log_idx
        writer.add_scalar('Loss/total', loss, log_idx)
        writer.add_scalar('Loss/bce', loss_bce, log_idx)
        writer.add_scalar('Loss/kld', loss_kld, log_idx)
        writer.add_scalar('Gradient_norm/before', total_norm, log_idx)
        writer.add_scalar('KL_weight', args.kl_weight, log_idx)
        log_idx += 1 

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip, norm_type=2)
            # Re-calculating and printing gradient norm
            total_norm = calc_grad_norm_2(model)
            writer.add_scalar('Gradient_norm/clipped', total_norm, log_idx)

        train_losses.append((loss.item(), loss_bce, loss_kld))
        train_loss += loss
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data128),
                                                                            len(train_loader.dataset),
                                                                            100. * batch_idx / len(train_loader),
                                                                            loss / len(data128)))
            
            n = min(data128.size(0), 8)
            
    writer.flush()
    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))


def train_wtvae_128_fixed_wt(epoch, model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    model.train()
    train_loss = 0
    anneal_rate = (1.0 - args.kl_start) / (args.kl_warmup * len(train_loader))

    for batch_idx, data in enumerate(train_loader):
        args.kl_weight = min(1.0, args.kl_weight + anneal_rate)
        data128 = data[0]
        data512 = data[1]
        if model.cuda:
            data128 = data128.to(model.device)
            data512 = data512.to(model.device)

        optimizer.zero_grad()
        
        wt_data, mu, logvar = model(data128)
        loss, loss_bce, loss_kld = model.loss_function(data512, wt_data, mu, logvar, kl_weight=args.kl_weight)
        loss.backward()
    
        # Calculating and printing gradient norm
        total_norm = calc_grad_norm_2(model)

        global log_idx
        writer.add_scalar('Loss/total', loss, log_idx)
        writer.add_scalar('Loss/bce', loss_bce, log_idx)
        writer.add_scalar('Loss/kld', loss_kld, log_idx)
        writer.add_scalar('Gradient_norm/before', total_norm, log_idx)
        writer.add_scalar('KL_weight', args.kl_weight, log_idx)
        log_idx += 1 

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip, norm_type=2)
            # Re-calculating and printing gradient norm
            total_norm = calc_grad_norm_2(model)
            writer.add_scalar('Gradient_norm/clipped', total_norm, log_idx)

        train_losses.append((loss.item(), loss_bce, loss_kld))
        train_loss += loss
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data128),
                                                                            len(train_loader.dataset),
                                                                            100. * batch_idx / len(train_loader),
                                                                            loss / len(data128)))
            
            n = min(data128.size(0), 8)
            
    writer.flush()
    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))


def train_iwtvae(epoch, wt_model, iwt_model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    iwt_model.train()
    train_loss = 0
    
    for batch_idx, data in enumerate(train_loader):
        
        data0 = data.to(iwt_model.device)
        data1 = data.to(wt_model.device)

        optimizer.zero_grad()
        
        # Get Y
        Y = wt_model(data1)
        
        # Zeroing out all other patches, if given zero arg
        if args.zero:
            Y = zero_patches(Y, num_wt=args.num_iwt)

        x_hat, mu, var = iwt_model(data0, Y.to(iwt_model.device))
        
        loss, loss_bce, loss_kld = iwt_model.loss_function(data0, x_hat, mu, var)
        loss.backward()

        # Calculating and printing gradient norm
        total_norm = calc_grad_norm_2(iwt_model)

        # Calculating and printing gradient norm
        global log_idx
        writer.add_scalar('Loss/total', loss, log_idx)
        writer.add_scalar('Loss/bce', loss_bce, log_idx)
        writer.add_scalar('Loss/kld', loss_kld, log_idx)
        writer.add_scalar('Gradient_norm/before', total_norm, log_idx)
        writer.add_scalar('KL_weight', args.kl_weight, log_idx)
        log_idx += 1 

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip, norm_type=2)
            # Re-calculating total norm after gradient clipping
            total_norm = calc_grad_norm_2(iwt_model)
            writer.add_scalar('Gradient_norm/clipped', total_norm, log_idx)
        
        train_losses.append([loss.cpu().item(), loss_bce.cpu().item(), loss_kld.cpu().item()])
        train_loss += loss

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(iwt_model.parameters(), max_norm=10000, norm_type=2)

        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
                                                                           len(train_loader.dataset),
                                                                           100. * batch_idx / len(train_loader),
                                                                           loss / len(data)))
            
            n = min(data.size(0), 8)  

    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))


# def train_iwtvae_512(epoch, wt_model, iwt_model, optimizer, train_loader, train_losses, args):
#     # toggle model to train mode
#     iwt_model.train()
#     train_loss = 0
    
#     for batch_idx, data in enumerate(train_loader):
        
#         data0 = data.to(iwt_model.devices[0])
#         data1 = data.to(iwt_model.devices[1])

#         optimizer.zero_grad()
        
#         # Get Y
#         Y = wt_model(data1)[0]

#         x_hat, mu, var = iwt_model(data0, Y.to(iwt_model.devices[0]))
#         # Fix loss function
#         loss = iwt_model.loss_function(data0, x_hat, mu, var)
#         loss.backward()
        
#         train_losses.append(loss.item())
#         train_loss += loss
#         optimizer.step()
#         if batch_idx % args.log_interval == 0:
#             logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
#                                                                            len(train_loader.dataset),
#                                                                            100. * batch_idx / len(train_loader),
#                                                                            loss / len(data)))
            
#             n = min(data.size(0), 8)  

#     logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))

def train_fullvae(epoch, full_model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    full_model.train()
    full_model.wt_model.train()
    full_model.iwt_model.train()
    train_loss = 0
    
    for batch_idx, data in enumerate(train_loader):
        optimizer.zero_grad()
        
        y, mu_wt, logvar_wt, x_hat, mu, var = full_model(data)
        
        loss, loss_bce, loss_kld = full_model.loss_function(data, y, mu_wt, logvar_wt, x_hat, mu, var)
        loss.backward()
        
        train_losses.append([loss.cpu().item(), loss_bce.cpu().item(), loss_kld.cpu().item()])
        train_loss += loss
        
        # Calculating and printing gradient norm
        total_norm = 0
        for p in full_model.parameters():
            # If frozen parameters, then skip
            if not p.requires_grad:
                continue
            param_norm = p.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
        total_norm = total_norm ** (1. / 2)
        logging.info('Gradient Norm: {}'.format(total_norm))

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(full_model.parameters(), max_norm=10000, norm_type=2)

        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
                                                                           len(train_loader.dataset),
                                                                           100. * batch_idx / len(train_loader),
                                                                           loss / len(data)))
            
            n = min(data.size(0), 8)  

    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))


def train_wtcnn(epoch, model, optimizer, train_loader, train_losses, args, writer):
    # toggle model to train mode
    model.train()
    train_loss = 0

    for batch_idx, data in enumerate(train_loader):
        
        if model.cuda:
            data = data.to(model.device)

        optimizer.zero_grad()
        
        wt_data = model(data)
        loss = model.loss_function(data, wt_data)
        loss.backward()

        # Calculating and printing gradient norm
        total_norm = 0
        for p in model.parameters():
            param_norm = p.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
        total_norm = total_norm ** (1. / 2)

        global log_idx
        writer.add_scalar('Loss/bce', loss, log_idx)
        writer.add_scalar('Gradient_norm/before', total_norm, log_idx)
        log_idx += 1 

        # Gradient clipping
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip, norm_type=2)
            # Calculating and printing gradient norm
            total_norm = 0
            for p in model.parameters():
                param_norm = p.grad.data.norm(2)
                total_norm += param_norm.item() ** 2
            total_norm = total_norm ** (1. / 2)
            writer.add_scalar('Gradient_norm/clipped', total_norm, log_idx)

        train_losses.append(loss.cpu().item())
        train_loss += loss
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
                                                                            len(train_loader.dataset),
                                                                            100. * batch_idx / len(train_loader),
                                                                            loss / len(data)))
            
            n = min(data.size(0), 8)
            
    writer.flush()
    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))
