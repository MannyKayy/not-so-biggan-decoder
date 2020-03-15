import sys
from utils.utils import zero_patches
import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(message)s')

def train_wtvae(epoch, model, optimizer, train_loader, train_losses, args):
    # toggle model to train mode
    model.train()
    train_loss = 0

    for batch_idx, data in enumerate(train_loader):
        
        if model.cuda:
            data = data.to(model.device)

        optimizer.zero_grad()
        
        wt_batch, mu, logvar = model(data)
        loss = model.loss_function(wt_batch, data, mu, logvar)
        loss.backward()
        
        train_losses.append(loss.item())
        train_loss += loss
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data),
                                                                            len(train_loader.dataset),
                                                                            100. * batch_idx / len(train_loader),
                                                                            loss / len(data)))
            
            n = min(data.size(0), 8)
            

    logging.info('====> Epoch: {} Average loss: {:.4f}'.format(epoch, train_loss / len(train_loader.dataset)))

def train_iwtvae(epoch, wt_model, iwt_model, optimizer, train_loader, train_losses, args):
    # toggle model to train mode
    iwt_model.train()
    train_loss = 0
    
    for batch_idx, data in enumerate(train_loader):
        
        data0 = data.to(iwt_model.devices[0])
        data1 = data.to(iwt_model.devices[1])

        optimizer.zero_grad()
        
        # Get Y
        Y = wt_model(data1)[0]
        
        # Zeroing out all other patches, if given zero arg
        if args.zero:
            Y = zero_patches(Y, args.num_iwt)

        x_hat, mu, var = iwt_model(data0, Y.to(iwt_model.devices[0]))
        
        loss, loss_bce, loss_kld = iwt_model.loss_function(data0, x_hat, mu, var)
        loss.backward()
        
        train_losses.append([loss.item(), loss_bce.item(), loss_kld.item()])
        train_loss += loss
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

def train_fullvae(epoch, full_model, optimizer, train_loader, train_losses, args):
    # toggle model to train mode
    full_model.wt_model.train()
    full_model.iwt_model.train()
    train_loss = 0
    
    for batch_idx, data in enumerate(train_loader):
        optimizer.zero_grad()
        
        y, mu_wt, logvar_wt, x_hat, mu, var = full_model(data)
        
        loss, loss_bce, loss_kld = full_model.loss_function(data, y, mu_wt, logvar_wt, x_hat, mu, var)
        loss.backward()
        
        train_losses.append([loss.item(), loss_bce.item(), loss_kld.item()])
        train_loss += loss
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


