import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Function
import numpy as np
import math
import sys


class BinarizeF(Function):
    '''
    >0: 1 <0:-1
    '''

    @staticmethod
    def forward(cxt, input):
        output = input.new(input.size())
        output[input >= 0] = 1
        output[input < 0] = -1

        return output

    @staticmethod
    def backward(cxt, grad_output):
        grad_input = grad_output.clone()
        return grad_input


# aliases
binarize = BinarizeF.apply


class ClipF(Function):

    @staticmethod
    def forward(ctx, input):
        output = input.clone().detach()
        # output = input.new(input.size())
        output[input >= 1] = 1
        output[input <= 0] = 0
        ctx.save_for_backward(input)
        return output

    @staticmethod
    def backward(ctx, grad_output):
        input, = ctx.saved_tensors
        grad_input = grad_output.clone()
        grad_input[input >= 1] = 0
        grad_input[input <= 0] = 0
        return grad_input


# aliases
clipfunc = ClipF.apply

#p-layer
class BinaryLinear(nn.Linear):

    def do_slp_via_th(self, input_ori, w_ori):
        p = input_ori
        d = 4 * p * (1 - p)
        e = (2 * p - 1)
        # e_sq = torch.tensor(1)
        w = w_ori

        sum_of_sq = (d + e.pow(2)).sum(-1)
        sum_of_sq = sum_of_sq.unsqueeze(-1)
        sum_of_sq = sum_of_sq.expand(p.shape[0], w.shape[0])

        diag_p = torch.diag_embed(e)

        p_w = torch.matmul(w, diag_p)

        z_p_w = torch.zeros_like(p_w)
        shft_p_w = torch.cat((p_w, z_p_w), -1)

        sum_of_cross = torch.zeros_like(p_w)
        length = p.shape[1]

        for shft in range(1, length):
            sum_of_cross += shft_p_w[:, :, 0:length] * shft_p_w[:, :, shft:length + shft]

        sum_of_cross = sum_of_cross.sum(-1)

        return (sum_of_sq + 2 * sum_of_cross) / (length ** 2)

    def forward(self, input):
        binary_weight = binarize(self.weight)
        if self.bias is None:
            # print(input,binary_weight,self.do_slp_via_th(input, binary_weight))
            # sys.exit(0)
            return self.do_slp_via_th(input, binary_weight)

        else:

            bias_one = torch.ones(input.shape[0], 1)
            new_input = torch.cat((input, bias_one), -1)
            bias = clipfunc(self.bias).unsqueeze(1)
            new_weight = binary_weight
            new_weight = torch.cat((new_weight, bias), -1)
            return self.do_slp_via_th(new_input, new_weight)


    def reset_parameters(self):
        # Glorot initialization
        in_features, out_features = self.weight.size()
        stdv = math.sqrt(1.5 / (in_features + out_features))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.zero_()

        self.weight.lr_scale = 1. / stdv





class BinaryLinearClassic(nn.Linear):

    def forward(self, input):
        binary_weight = binarize(self.weight)
        if self.bias is None:
            output = F.linear(input, binary_weight)
            # print(input,binary_weight, input.shape[-1])
            output = torch.div(output, input.shape[-1])
            # output = torch.pow(output, 2)

            return output
        else:
            print("Not Implement")
            sys.exit(0)

    def reset_parameters(self):
        # Glorot initialization
        in_features, out_features = self.weight.size()
        stdv = math.sqrt(1.5 / (in_features + out_features))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.zero_()

        self.weight.lr_scale = 1. / stdv



#u-layer
class BinaryLinearQuantumFirstLAYER(nn.Linear):

    def forward(self, input):
        binary_weight = binarize(self.weight)
        if self.bias is None:
            # print(binary_weight)
            output = F.linear(input, binary_weight)
            # print(input,binary_weight, math.sqrt(input.shape[-1]))
            
            output = torch.div(output, math.sqrt(input.shape[-1]))
            output = torch.pow(output, 2)

            return output
        else:
            print("Not Implement")
            sys.exit(0)

    def reset_parameters(self):
        # Glorot initialization
        in_features, out_features = self.weight.size()
        stdv = math.sqrt(1.5 / (in_features + out_features))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.zero_()

        self.weight.lr_scale = 1. / stdv

