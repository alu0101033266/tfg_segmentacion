

USER = 'enrique'
TARGET_CLASS = 'flint'
DATASET_NAME = 'dataset_silex_combinado'

#actualizar path con la ruta en el drive de cada uno
COLAB_PATH = '/content/gdrive/MyDrive/TFG/'


DATE_DIR_NAME = 'enrique_flint_pspnet_xception_2025-03-30_13-02-11'
TRAIN = True # False
GET_TEST_RESULTS = True

#ValueError: InceptionV4 encoder does not support dilated mode due to pooling operation for downsampling!
#ValueError: 'VGG' models do not support dilated mode due to Max Pooling operations for downsampling!
#completado PSPNET con resnet50, vgg19, inceptionv4, xception
#completado deeplavv3 con resnet50
ARCH = "pspnet"
# completados:
ENCODER = 'xception'  # vgg19, inceptionv4, xception

MAX_EPOCHS = 40
BATCH_SIZE = 16
TRAIN_SIZE = 0.7
VAL_SIZE = 0.2

from google.colab import drive

drive.mount('/content/gdrive', force_remount=True)

!pip install segmentation-models-pytorch
!pip install pytorch-lightning

import os
import torch
import matplotlib.pyplot as plt
import pytorch_lightning as pl
import segmentation_models_pytorch as smp

from pprint import pprint
from torch.utils.data import DataLoader
from torch.utils.data import DataLoader, Dataset, random_split

import cv2
import numpy as np
from PIL import Image
import albumentations as alb
from albumentations.pytorch import ToTensorV2
import random

path = "\'" + os.path.join(COLAB_PATH,DATASET_NAME+ '.rar') + "\'"
!unrar x $path

class SedimentsDataset(Dataset):



    CLASSES = ['_background_','bone','charcoal','flint']

    def __init__(
            self,
            images_dir,
            masks_dir,
            target_class='bone',
            augmentation=None,
            preprocessing=None,
            transform=None,
            mode = 'train'
    ):
        self.ids = os.listdir(images_dir)
        #print("Antes:" , self.ids)
        self.mode = mode

        random.seed(42)

        # Shuffle the data
        data_copy = self.ids[:]
        data_copy.sort()
        random.shuffle(data_copy)
        #print("Despues:" , data_copy)

        # Determine the split indices
        total_len = len(data_copy)
        train_size = TRAIN_SIZE
        val_size = VAL_SIZE

        train_end = int(total_len * train_size)
        val_end = train_end + int(total_len * val_size)

        # Split the data
        if mode == 'train':
          self.ids = data_copy[:train_end]
        elif mode == 'val':
          self.ids = data_copy[train_end:val_end]
        else:
          self.ids = data_copy[val_end:]

        self.images_fps = [os.path.join(images_dir, image_id) for image_id in self.ids]
        self.masks_fps = [os.path.join(masks_dir, image_id) for image_id in self.ids]

        # convert str names to class values on masks
        self.class_value = self.CLASSES.index(target_class.lower())
        self.augmentation = augmentation
        self.preprocessing = preprocessing
        self.transform = transform

    def __getitem__(self, i):
        #print(self.images_fps[i])
        # read data
        image = cv2.imread(self.images_fps[i])
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # image = np.array(Image.open(self.images_fps[i]).convert("RGB"))
        # mask = np.array(Image.open(self.masks_fps[i]))
        # print(type(mask))
        # mask = self._preprocess_mask(mask)

        mask = cv2.imread(self.masks_fps[i], 0)
        mask = mask.squeeze()
        mask = mask.astype(np.float32)
        mask[mask != self.class_value] = 0.0
        mask[mask == self.class_value] = 1.0

        # extract certain classes from mask (e.g. cars)
        # masks = [(mask == v) for v in self.class_values]
        # mask = np.stack(masks, axis=-1).astype(np.float32)
        # print("mask shape:" , mask.shape)
        # print("mask type:" , type(mask))
        # print("image shape:" , image.shape)
        # print("image type:" , type(image))

        image = np.array(Image.fromarray(image).resize((512, 512), Image.BILINEAR))
        mask = np.array(Image.fromarray(mask).resize((512, 512), Image.NEAREST))

        if self.mode == 'train' and self.transform:
            augmented = self.transform(image=image, mask=mask)
            image = augmented['image']
            mask = augmented['mask']

        image = np.moveaxis(image, -1, 0)
        mask = np.expand_dims(mask, 0)

        # # apply augmentations
        # if self.augmentation:
        #     sample = self.augmentation(image=image, mask=mask)
        #     image, mask = sample['image'], sample['mask']

        # # apply preprocessing
        # if self.preprocessing:
        #     sample = self.preprocessing(image=image, mask=mask)
        #     image, mask = sample['image'], sample['mask']

        # if self.transform:
        #     image, mask = self.transform(image, mask)


        return {"image": image,"mask" : mask}

    def __len__(self):
        return len(self.ids)

transform = alb.Compose([
    alb.HorizontalFlip(p=0.5),
    alb.VerticalFlip(p=0.5),
    #rotar 90
])


data_dir = os.path.join('/content/', DATASET_NAME)
images_dir = os.path.join(data_dir,'images')
labels_dir = os.path.join(data_dir,'labels')


train_dataset = SedimentsDataset(images_dir, labels_dir, target_class = TARGET_CLASS,transform = transform, mode = 'train')
val_dataset = SedimentsDataset(images_dir, labels_dir, target_class = TARGET_CLASS, mode = 'val')
test_dataset = SedimentsDataset(images_dir, labels_dir, target_class = TARGET_CLASS, mode = 'test')


train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)


# Verificar tamaños de los dataloaders
print(f'Tamaño del conjunto de entrenamiento: {len(train_loader.dataset)}')
print(f'Tamaño del conjunto de validación: {len(val_loader.dataset)}')
print(f'Tamaño del conjunto de testeo: {len(test_loader.dataset)}')


#It is a good practice to check datasets don`t intersects with each other
assert set(test_dataset.ids).isdisjoint(set(train_dataset.ids))
assert set(test_dataset.ids).isdisjoint(set(val_dataset.ids))
assert set(train_dataset.ids).isdisjoint(set(val_dataset.ids))

sample = train_dataset[0]
plt.subplot(1,2,1)
plt.imshow(sample["image"].transpose(1, 2, 0)) # for visualization we have to transpose back to HWC
plt.subplot(1,2,2)
plt.imshow(sample["mask"].squeeze())  # for visualization we have to remove 3rd dimension of mask
plt.show()

sample = val_dataset[0]
plt.subplot(1,2,1)
plt.imshow(sample["image"].transpose(1, 2, 0)) # for visualization we have to transpose back to HWC
plt.subplot(1,2,2)
plt.imshow(sample["mask"].squeeze())  # for visualization we have to remove 3rd dimension of mask
plt.show()

sample = test_dataset[0]
plt.subplot(1,2,1)
plt.imshow(sample["image"].transpose(1, 2, 0)) # for visualization we have to transpose back to HWC
plt.subplot(1,2,2)
plt.imshow(sample["mask"].squeeze())  # for visualization we have to remove 3rd dimension of mask
plt.show()

class SedimentsModel(pl.LightningModule):

    def __init__(self, arch, encoder_name, encoder_weights, in_channels, out_classes, **kwargs):
        super().__init__()
        self.train_step_outputs = []
        self.valid_step_outputs = []
        self.test_step_outputs = []
        self.model = smp.create_model(
            arch,
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=out_classes,
            output_stride=32, # Disable dilated mode by setting output_stride to 32
            **kwargs # keep kwargs for flexibility
        )
     #   self.model = smp.create_model(
      #      arch, encoder_name=encoder_name, encoder_weights = encoder_weights, in_channels=in_channels, classes=out_classes, **kwargs
       # )
        self.save_hyperparameters()
        # preprocessing parameteres for image
        params = smp.encoders.get_preprocessing_params(encoder_name)
        self.register_buffer("std", torch.tensor(params["std"]).view(1, 3, 1, 1))
        self.register_buffer("mean", torch.tensor(params["mean"]).view(1, 3, 1, 1))

        # for image segmentation dice loss could be the best first choice
        self.loss_fn = smp.losses.DiceLoss(smp.losses.BINARY_MODE, from_logits=True)

    def forward(self, image):
        # normalize image here
        image = (image - self.mean) / self.std
        mask = self.model(image)
        return mask

    def shared_step(self, batch, stage):

        image = batch["image"]

        # Shape of the image should be (batch_size, num_channels, height, width)
        # if you work with grayscale images, expand channels dim to have [batch_size, 1, height, width]
        assert image.ndim == 4

        # Check that image dimensions are divisible by 32,
        # encoder and decoder connected by `skip connections` and usually encoder have 5 stages of
        # downsampling by factor 2 (2 ^ 5 = 32); e.g. if we have image with shape 65x65 we will have
        # following shapes of features in encoder and decoder: 84, 42, 21, 10, 5 -> 5, 10, 20, 40, 80
        # and we will get an error trying to concat these features
        h, w = image.shape[2:]
        assert h % 32 == 0 and w % 32 == 0

        mask = batch["mask"]

        # Shape of the mask should be [batch_size, num_classes, height, width]
        # for binary segmentation num_classes = 1
        assert mask.ndim == 4

        # Check that mask values in between 0 and 1, NOT 0 and 255 for binary segmentation
        assert mask.max() <= 1.0 and mask.min() >= 0

        logits_mask = self.forward(image)

        # Predicted mask contains logits, and loss_fn param `from_logits` is set to True
        loss = self.loss_fn(logits_mask, mask)


        # Lets compute metrics for some threshold
        # first convert mask values to probabilities, then
        # apply thresholding
        prob_mask = logits_mask.sigmoid()
        pred_mask = (prob_mask > 0.5).float()

        # We will compute IoU metric by two ways
        #   1. dataset-wise
        #   2. image-wise
        # but for now we just compute true positive, false positive, false negative and
        # true negative 'pixels' for each image and class
        # these values will be aggregated in the end of an epoch
        tp, fp, fn, tn = smp.metrics.get_stats(pred_mask.long(), mask.long(), mode="binary")

        output= {
            "loss": loss,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }
        if stage == "train":
          self.train_step_outputs.append(output)
        elif stage == "test":
          self.test_step_outputs.append(output)
        else:
          self.valid_step_outputs.append(output)

        return output

    def shared_epoch_end(self, stage):
        # aggregate step metics
        if stage == "train":
          outputs = self.train_step_outputs
        elif stage == "test":
          outputs = self.test_step_outputs
        else:
          outputs = self.valid_step_outputs

        tp = torch.cat([x["tp"] for x in outputs])
        fp = torch.cat([x["fp"] for x in outputs])
        fn = torch.cat([x["fn"] for x in outputs])
        tn = torch.cat([x["tn"] for x in outputs])

        # per image IoU means that we first calculate IoU score for each image
        # and then compute mean over these scores
        per_image_iou = smp.metrics.iou_score(tp, fp, fn, tn, reduction="micro-imagewise")

        # dataset IoU means that we aggregate intersection and union over whole dataset
        # and then compute IoU score. The difference between dataset_iou and per_image_iou scores
        # in this particular case will not be much, however for dataset
        # with "empty" images (images without target class) a large gap could be observed.
        # Empty images influence a lot on per_image_iou and much less on dataset_iou.
        dataset_iou = smp.metrics.iou_score(tp, fp, fn, tn, reduction="micro")

        metrics = {
            f"{stage}_per_image_iou": per_image_iou,
            f"{stage}_dataset_iou": dataset_iou,
        }

        self.log_dict(metrics, prog_bar=True)
        if stage == "train":
          self.train_step_outputs.clear()  # free memory
        elif stage == "test":
          self.test_step_outputs.clear()  # free memory
        else:
          self.valid_step_outputs.clear()  # free memory



    def training_step(self, batch, batch_idx):
        return self.shared_step(batch, "train")

    def on_train_epoch_end(self):
        return self.shared_epoch_end("train")

    def validation_step(self, batch, batch_idx):
        return self.shared_step(batch, "valid")

    def on_validation_epoch_end(self):
        return self.shared_epoch_end("valid")

    def test_step(self, batch, batch_idx):
        return self.shared_step(batch, "test")

    def on_test_epoch_end(self):
        return self.shared_epoch_end("test")

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.0001)

import glob
from datetime import datetime

def encontrar_modelo_mas_reciente(directorio, extension='.ckpt'):
    archivos = glob.glob(os.path.join(directorio, '**', f'*{extension}'), recursive=True)
    if not archivos:
        return None
    return max(archivos, key=os.path.getmtime)

def encontrar_mejor_modelo(directorio, extension='.ckpt'):
    archivos = glob.glob(os.path.join(directorio, '**', f'best_model-*{extension}'), recursive=True)
    if not archivos:
        return None
    return max(archivos, key=os.path.getmtime)


from pytorch_lightning.callbacks import ModelCheckpoint

best_model_checkpoint = ModelCheckpoint(
    monitor="valid_dataset_iou",      # Track validation loss
    mode="max",              # Save model with the lowest val_loss
    save_top_k=1,            # Keep only the best model
    filename="best_model-{epoch:02d}-{valid_dataset_iou:.2f}"
)

# Last epoch checkpoint
last_epoch_checkpoint = ModelCheckpoint()


if (DATE_DIR_NAME is not None):
  date_dir_name = DATE_DIR_NAME
  if TRAIN:
    ckpt_path = encontrar_modelo_mas_reciente(os.path.join(COLAB_PATH,'Results',date_dir_name))
    model = SedimentsModel(ARCH, ENCODER, encoder_weights = 'imagenet', in_channels=3, out_classes=1)
    trainer = pl.Trainer(callbacks = [best_model_checkpoint, last_epoch_checkpoint],
                         max_epochs=MAX_EPOCHS,
                         default_root_dir = os.path.join(COLAB_PATH,'Results',date_dir_name))
    trainer.fit(model, ckpt_path = ckpt_path,
                train_dataloaders=train_loader,
                val_dataloaders=val_loader,)
  else:
    ckpt_path = encontrar_mejor_modelo(os.path.join(COLAB_PATH,'Results',date_dir_name))
    model = SedimentsModel.load_from_checkpoint(ckpt_path)
    trainer = pl.Trainer( max_epochs=MAX_EPOCHS,
                          default_root_dir = os.path.join(COLAB_PATH,'Results',date_dir_name))

else:
  model = SedimentsModel(ARCH, ENCODER, encoder_weights = 'imagenet', in_channels=3, out_classes=1)

  now = datetime.now()
  date_dir_name = USER + "_" + TARGET_CLASS + "_" + ARCH + "_" + ENCODER + "_" + now.strftime("%Y-%m-%d_%H-%M-%S")

  trainer = pl.Trainer(callbacks = [best_model_checkpoint, last_epoch_checkpoint],
      max_epochs=MAX_EPOCHS,
      default_root_dir = os.path.join(COLAB_PATH,'Results',date_dir_name)
  )

  trainer.fit(
      model,
      train_dataloaders=train_loader,
      val_dataloaders=val_loader,
  )

# run validation dataset
valid_metrics = trainer.validate(model, dataloaders=val_loader, verbose=False)
pprint(valid_metrics)

# run test dataset
test_metrics = trainer.test(model, dataloaders=test_loader, verbose=False)
pprint(test_metrics)

#creamos el archivo con los resultados
results_file_path = os.path.join(COLAB_PATH,'Results',date_dir_name,'IoU.txt')
with open(results_file_path, 'w') as archivo:
    archivo.write(f"Clase: {TARGET_CLASS}\n")
    archivo.write(f"Arquitectura: {ARCH}\n")
    archivo.write(f"Encoder: {ENCODER}\n")
    for clave, valor in valid_metrics[0].items():
        archivo.write(f"{clave}: {valor}\n")
    for clave, valor in test_metrics[0].items():
        archivo.write(f"{clave}: {valor}\n")

#Results visualization and saving images
result_images_paths = os.path.join(COLAB_PATH,'Results',date_dir_name,'Test images')
if not os.path.exists(result_images_paths):
  os.makedirs(result_images_paths)

batch = next(iter(test_loader))
with torch.no_grad():
    model.eval()
    logits = model(batch["image"])
pr_masks = logits.sigmoid()

cont = 1
for image, gt_mask, pr_mask in zip(batch["image"], batch["mask"], pr_masks):
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 3, 1)
    plt.imshow(image.numpy().transpose(1, 2, 0))  # convert CHW -> HWC
    plt.title("Image")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.imshow(gt_mask.numpy().squeeze()) # just squeeze classes dim, because we have only one class
    plt.title("Ground truth")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.imshow(pr_mask.numpy().squeeze()) # just squeeze classes dim, because we have only one class
    plt.title("Prediction")
    plt.axis("off")
    plt.savefig(os.path.join(result_images_paths,'images_' + str(cont) + '.png'))

    plt.show()
    cont += 1
