from tkinter import filedialog, messagebox
from tkinter import *
from model import Model
import matplotlib.pyplot as plt
from collections import OrderedDict

import base64
from PIL import Image, ImageTk
import glob
import numpy as np
import os
import random
import torch

torch.set_default_tensor_type('torch.FloatTensor')

class Window(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master = master
        self.init_window()

        self.arch_file_name = None
        self.arch = Model().float()
        self.dataroot = '/home/tom/data/ellipses3/test'
        self.files = glob.glob(os.path.join(self.dataroot, '*.pkl'))

    def init_window(self):
        self.master.title('Geogan viewer')
        self.pack(fill=BOTH, expand=1)

        menu = Menu(self.master)
        self.master.config(menu=menu)
        file = Menu(menu)
        file.add_command(label='Exit', command=exit)

        menu.add_cascade(label='File', menu=file)
        edit = Menu(menu)
        edit.add_command(label='Undo')
        menu.add_cascade(label='Edit', menu=edit)

        archButton = Button(self, text='Choose arch file', command=self.build_arch)
        archButton.place(x=0, y=0)

        chooseDatarootButton = Button(self, text='Choose dataroot', command=self.choose_dataroot)
        chooseDatarootButton.place(x=120, y=0)

        load_model_button = Button(self, text='Load model', command=self.load_model)
        load_model_button.place(x=240, y=0)

        random_image_button = Button(self, text='Get random image', command=self.set_random_image)
        random_image_button.place(x=100, y=300)

        blank_image = Image.fromarray(np.ones((256, 512, 3), dtype=np.uint8) * 127)
        blank_image_tk = ImageTk.PhotoImage(image=blank_image)

        self.input_image_pane = Label(self.master, image=blank_image_tk, height=255, width=512)
        self.input_image_pane.image = blank_image_tk
        self.input_image_pane.pack(fill=BOTH, expand=1)
        self.input_image_pane.place(x=0, y=40)

        self.output_div_image_pane = Label(self.master, image=blank_image_tk, height=255, width=512)
        self.output_div_image_pane.image = blank_image_tk
        self.output_div_image_pane.pack(fill=BOTH, expand=1)
        self.output_div_image_pane.place(x=540, y=40)

        self.output_disc_image_pane = Label(self.master, image=blank_image_tk, height=255, width=512)
        self.output_disc_image_pane.image = blank_image_tk
        self.output_disc_image_pane.pack(fill=BOTH, expand=1)
        self.output_disc_image_pane.place(x=540, y=340)

        self.slider = Scale(self.master, from_=0, to=100, orient=HORIZONTAL, command=self.display_discrete_image)
        self.slider.configure(length=300, sliderlength=30, resolution=0.1)
        self.slider.place(x=630, y=630)
        self.slider.pack()



    def build_arch(self):
        self.arch_file_name = filedialog.askopenfilename(initialdir='/home/tom/data/work/geology/geogan_checkpoints', title='Select architecture description file')

        self.arch.arch_from_slurm((self.arch_file_name))
        print(self.arch)


    def choose_dataroot(self):
        self.dataroot = filedialog.askdirectory(initialdir=os.getcwd(), title='Choose dataroot')
        self.files = glob.glob(os.path.join(self.dataroot, '*.pkl'))
        if len(self.files) == 0:
            messagebox.showerror('Error', "No pickle files in this location")
            self.dataroot = None


    def load_model(self):
        if self.arch == None:
            messagebox.showerror('Error', 'Define an architecture first')

        self.weights_filename = filedialog.askopenfilename(initialdir=os.path.dirname(self.arch_file_name),
                                                         title='Select model weights file')

        weights = torch.load(self.weights_filename)

        # def rename_keys(weights_dict):
        #     new_weights = OrderedDict()
        #
        #     for key, value in weights_dict.items():
        #         new_name = re.sub('model', '0', key)
        #
        #         if isinstance(value, OrderedDict):
        #             new_weights[new_name] = rename_keys(value)
        #         else:
        #             new_weights[new_name] = value
        #
        #     return new_weights
        #
        # new_state_dict = rename_keys(weights)

        self.arch.model.load_state_dict(weights)
        self.arch.model = self.arch.model.float()


    def display_discrete_image(self, slider_value):
        thresh = np.interp(slider_value, [0, 100], [0, 1.0])

        ridge_layer = np.ones(self.div_im.shape, dtype=bool)
        sub_layer = np.ones(self.div_im.shape, dtype=bool)
        ridge_layer[np.where(self.div_im < -thresh)] = False
        sub_layer[np.where(self.div_im > thresh)] = False
        plate_layer = np.logical_and(ridge_layer, sub_layer)

        out_disc = np.dstack((ridge_layer, plate_layer, sub_layer)).astype(np.uint8) * 255
        image = Image.fromarray(out_disc)
        out_disc_image_tk = ImageTk.PhotoImage(image=image)

        self.output_disc_image_pane.configure(image=out_disc_image_tk)
        self.output_disc_image_pane.image = out_disc_image_tk


    def set_random_image(self):
        if self.dataroot == None or len(self.files) == 0:
            messagebox.showinfo('Error', 'Set dataroot first')
            return

        pkl_file = random.sample(self.files, 1)[0]
        data = torch.load(pkl_file)

        disc_im = data['A']
        disc_im[:, :, 0][np.where(disc_im[:, :, 1])] = 1
        disc_im[:, :, 2][np.where(disc_im[:, :, 1])] = 1
        image = Image.fromarray(disc_im.astype(np.uint8) * 255)
        in_image_tk = ImageTk.PhotoImage(image=image)
        self.input_image_pane.configure(image=in_image_tk)
        self.input_image_pane.image = in_image_tk

        self.div_im = self.arch.model(torch.from_numpy(data['A'].transpose(2, 0, 1)).unsqueeze(0).float())
        self.div_im = self.div_im.detach().data.squeeze().numpy().transpose(1, 2, 0)[:,:,0]
        self.div_im = np.interp(self.div_im, [self.div_im.min(), 0, self.div_im.max()], [-1, 0, 1])

        image = Image.fromarray(((self.div_im + 1) / 2 * 255).astype(np.uint8))
        out_image_tk = ImageTk.PhotoImage(image=image)
        self.output_div_image_pane.configure(image=out_image_tk)
        self.output_div_image_pane.image = out_image_tk

        self.display_discrete_image(self.slider.get())



root = Tk()
root.geometry("1260x640")
app = Window(root)
root.mainloop()