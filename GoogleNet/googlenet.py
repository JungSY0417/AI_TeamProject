import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
import os

import pytorch_lightning as pl
from pytorch_lightning.metrics import functional as FM


def googlenet(learning_rate):
    model = GoogLeNet(learning_rate)
    model.load_state_dict(torch.load('/home/maylily/project/studing/AI_TeamProject/GoogleNet/googlenet-1378be20.pth'), strict=False)
    model.aux_logits = False

    fc_weights = model.fc.weight.data  # pytorch tensor
    model.fc3.weight.data[0] = fc_weights[288]
    model.fc3.weight.data[1] = fc_weights[290]
    model.fc3.weight.data[2] = fc_weights[293]

    fc_biases = model.fc.bias.data
    model.fc3.bias.data[0] = fc_biases[288]
    model.fc3.bias.data[1] = fc_biases[290]
    model.fc3.bias.data[2] = fc_biases[293]

    fc_aux1_weights = model.aux1.fc2.weight.data
    fc_aux1_biases = model.aux2.fc2.bias.data

    model.aux1.fc3.weight.data[0] = fc_aux1_weights[288]
    model.aux1.fc3.weight.data[1] = fc_aux1_weights[290]
    model.aux1.fc3.weight.data[2] = fc_aux1_weights[293]

    model.aux1.fc3.bias.data[0] = fc_aux1_biases[288]
    model.aux1.fc3.bias.data[1] = fc_aux1_biases[290]
    model.aux1.fc3.bias.data[2] = fc_aux1_biases[293]

    fc_aux2_weights = model.aux2.fc2.weight.data
    fc_aux2_biases = model.aux2.fc2.bias.data

    model.aux2.fc3.weight.data[0] = fc_aux2_weights[288]
    model.aux2.fc3.weight.data[1] = fc_aux2_weights[290]
    model.aux2.fc3.weight.data[2] = fc_aux2_weights[293]

    model.aux2.fc3.bias.data[0] = fc_aux2_biases[288]
    model.aux2.fc3.bias.data[1] = fc_aux2_biases[290]
    model.aux2.fc3.bias.data[2] = fc_aux2_biases[293]

    return model

class GoogLeNet(pl.LightningModule):
    def __init__(self, learning_rate) :
        super(GoogLeNet, self).__init__()

        self.aux_logits = True
        num_classes = 1000

        self.conv1 = BasicConv2d(3, 64, kernel_size=7, stride=2, padding=3)
        self.maxpool1 = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        self.conv2 = BasicConv2d(64, 64, kernel_size=1)
        self.conv3 = BasicConv2d(64, 192, kernel_size=3, padding=1)
        self.maxpool2 = nn.MaxPool2d(3, stride=2, ceil_mode=True)

        self.inception3a = Inception(192, 64, 96, 128, 16, 32, 32)
        self.inception3b = Inception(256, 128, 128, 192, 32, 96, 64)
        self.maxpool3 = nn.MaxPool2d(3, stride=2, ceil_mode=True)

        self.inception4a = Inception(480, 192, 96, 208, 16, 48, 64)
        self.inception4b = Inception(512, 160, 112, 224, 24, 64, 64)
        self.inception4c = Inception(512, 128, 128, 256, 24, 64, 64)
        self.inception4d = Inception(512, 112, 144, 288, 32, 64, 64)
        self.inception4e = Inception(528, 256, 160, 320, 32, 128, 128)
        self.maxpool4 = nn.MaxPool2d(2, stride=2, ceil_mode=True)

        self.inception5a = Inception(832, 256, 160, 320, 32, 128, 128)
        self.inception5b = Inception(832, 384, 192, 384, 48, 128, 128)

        self.aux1 = InceptionAux(512)
        self.aux2 = InceptionAux(528)

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(0.2)
        self.fc = nn.Linear(1024, 1000)
        self.fc3 = nn.Linear(1024, 3)

        self.lr = learning_rate
        self.loss = F.cross_entropy

    def _transform_input(self, x):
        x_ch0 = torch.unsqueeze(x[:, 0], 1) * (0.229 / 0.5) + (0.485 - 0.5) / 0.5
        x_ch1 = torch.unsqueeze(x[:, 1], 1) * (0.224 / 0.5) + (0.456 - 0.5) / 0.5
        x_ch2 = torch.unsqueeze(x[:, 2], 1) * (0.225 / 0.5) + (0.406 - 0.5) / 0.5
        x = torch.cat((x_ch0, x_ch1, x_ch2), 1)
        return x

    def _forward(self, x):
        # N x 3 x 224 x 224
        x = self.conv1(x)
        # N x 64 x 112 x 112
        x = self.maxpool1(x)
        # N x 64 x 56 x 56
        x = self.conv2(x)
        # N x 64 x 56 x 56
        x = self.conv3(x)
        # N x 192 x 56 x 56
        x = self.maxpool2(x)

        # N x 192 x 28 x 28
        x = self.inception3a(x)
        # N x 256 x 28 x 28
        x = self.inception3b(x)
        # N x 480 x 28 x 28
        x = self.maxpool3(x)
        # N x 480 x 14 x 14
        x = self.inception4a(x)
        # N x 512 x 14 x 14

        aux1 = None
        if self.training:
            aux1 = self.aux1(x)

        x = self.inception4b(x)
        # N x 512 x 14 x 14
        x = self.inception4c(x)
        # N x 512 x 14 x 14
        x = self.inception4d(x)
        # N x 528 x 14 x 14

        aux2 = None
        if self.training:
            aux2 = self.aux2(x)

        x = self.inception4e(x)
        # N x 832 x 14 x 14
        x = self.maxpool4(x)
        # N x 832 x 7 x 7
        x = self.inception5a(x)
        # N x 832 x 7 x 7
        x = self.inception5b(x)
        # N x 1024 x 7 x 7

        x = self.avgpool(x)
        # N x 1024 x 1 x 1
        x = torch.flatten(x, 1)
        # N x 1024
        x = self.dropout(x)
        x = self.fc3(x)
        # N x 3
        
        return x, aux2, aux1

    def forward(self, x):
        x = self._transform_input(x)
        x, aux1, aux2 = self._forward(x)
        return x
    
    def training_step(self, batch, batch_nb):
        x, y = batch
        y_hat = self(x)
        loss = self.loss(y_hat, y)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self.forward(x)
        loss = self.loss(y_hat, y)
        y_hat = F.softmax(y_hat, dim=1)
        acc = FM.accuracy(y_hat, y)

        metrics = {'val_acc': acc, 'val_loss': loss}
        self.log_dict(metrics)

    def test_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.loss(y_hat, y)
        y_hat = F.softmax(y_hat, dim=1)
        acc = FM.accuracy(y_hat, y)

        metrics = {'test_acc': acc, 'test_loss': loss}
        self.log_dict(metrics)

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self.lr, weight_decay=0.0001)

class Inception(nn.Module):
    def __init__(
        self,
        in_channels,
        ch1x1,
        ch3x3red,
        ch3x3,
        ch5x5red,
        ch5x5,
        pool_proj,
    ):
        super(Inception, self).__init__()
        self.branch1 = BasicConv2d(in_channels, ch1x1, kernel_size=1)

        self.branch2 = nn.Sequential(
            BasicConv2d(in_channels, ch3x3red, kernel_size=1),
            BasicConv2d(ch3x3red, ch3x3, kernel_size=3, padding=1)
        )

        self.branch3 = nn.Sequential(
            BasicConv2d(in_channels, ch5x5red, kernel_size=1),
            BasicConv2d(ch5x5red, ch5x5, kernel_size=3, padding=1)
        )

        self.branch4 = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=1, padding=1, ceil_mode=True),
            BasicConv2d(in_channels, pool_proj, kernel_size=1)
        )

    def _forward(self, x):
        branch1 = self.branch1(x)
        branch2 = self.branch2(x)
        branch3 = self.branch3(x)
        branch4 = self.branch4(x)
        outputs = [branch1, branch2, branch3, branch4]
        return outputs

    def forward(self, x):
        return torch.cat(self._forward(x), 1)


class InceptionAux(nn.Module):
    def __init__(self, in_channels):
        super(InceptionAux, self).__init__()
        self.conv = BasicConv2d(in_channels, 128, kernel_size=1)

        self.fc1 = nn.Linear(2048, 1024)
        self.fc2 = nn.Linear(1024, 1000)  # original
        self.fc3 = nn.Linear(1024, 3)  # copied

    def forward(self, x):
        # aux1: N x 512 x 14 x 14, aux2: N x 528 x 14 x 14
        x = F.adaptive_avg_pool2d(x, (4, 4))
        # aux1: N x 512 x 4 x 4, aux2: N x 528 x 4 x 4
        x = self.conv(x)
        # N x 128 x 4 x 4
        x = torch.flatten(x, 1)
        # N x 2048
        x = F.relu(self.fc1(x), inplace=True)
        # N x 1024
        x = F.dropout(x, 0.7, training=self.training)
        # N x 3
        x = self.fc3(x)
        return x

class BasicConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, **kwargs):
        super(BasicConv2d, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, bias=False, **kwargs)
        self.bn = nn.BatchNorm2d(out_channels, eps=0.001)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        return F.relu(x, inplace=True)