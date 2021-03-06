# Approximation Attack 1 : Average Rank Thresholding

import os
import pickle

import numpy as np
import tensorflow as tf
from nltk.translate.bleu_score import sentence_bleu
from sklearn import svm
from sklearn.metrics import accuracy_score

from models import UNITS, Decoder, Encoder
from train import Translate

BATCH_SIZE = 64
###################################

with open('data/inp_lang.pickle', 'rb') as handle, open('data/targ_lang.pickle', 'rb') as handle2:
    inp_lang = pickle.load(handle)
    targ_lang = pickle.load(handle2)


in_train, in_train_label = np.load(
    'data/in_train.npy'), np.load('data/in_train_label.npy')
out_train, out_train_label = np.load(
    'data/out_train.npy'), np.load('data/out_train_label.npy')
in_test, in_test_label = np.load(
    'data/in_test.npy'), np.load('data/in_test_label.npy')
out_test, out_test_label = np.load(
    'data/out_test.npy'), np.load('data/out_test_label.npy')


vocab_inp_size = len(inp_lang.word_index)+1
vocab_tar_size = len(targ_lang.word_index)+1

encoder = Encoder(vocab_inp_size, BATCH_SIZE)
decoder = Decoder(vocab_tar_size, BATCH_SIZE)
max_length_targ, max_length_inp = 11, 16
optimizer = tf.keras.optimizers.Adam()

checkpoint_dir = './checkpoints/training_checkpoints'
shadow_checkpoint_dir = './checkpoints/shadow_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(optimizer=optimizer,
                                 encoder=encoder,
                                 decoder=decoder)


minimum = min(len(in_train), len(out_train))


def translate_and_get_indices(tr, tar, pred_probs):
    res = ''
    for word in tar:
        if word != 0:
            res += targ_lang.index_word[word] + ' '
    res = res.split(' ', 1)[1]

    ### score = sentence_bleu([tr.split()], res.split())

    indices = []

    for word, prob in zip(res.split(), pred_probs):
        temp = (-prob).argsort()[:len(prob)]
        ranks = np.empty_like(temp)
        ranks[temp] = np.arange(len(prob))
        ind = targ_lang.word_index[word]
        indices.append(ranks[ind])

    return indices


translator = Translate(encoder, decoder, UNITS,
                       inp_lang, targ_lang, max_length_targ, max_length_inp)
in_train_indices = []
i = 0
for ten, tar in zip(in_train, in_train_label):
    i += 1
    if i > minimum:
        break
    tr, pred_probs = translator.translate(ten, True)
    indices = translate_and_get_indices(tr, tar, pred_probs)
    in_train_indices.append(np.mean(indices))


out_train_indices = []
i = 0
for ten, tar in zip(out_train, out_train_label):
    i += 1
    if i > minimum:
        break
    tr, pred_probs = translator.translate(ten, True)
    indices = translate_and_get_indices(tr, tar, pred_probs)
    out_train_indices.append(np.mean(indices))

in_test_indices = []
i = 0
for ten, tar in zip(in_test, in_test_label):
    i += 1
    if i > minimum:
        break
    tr, pred_probs = translator.translate(ten, True)
    indices = translate_and_get_indices(tr, tar, pred_probs)
    in_test_indices.append(np.mean(indices))

out_test_indices = []
i = 0
for ten, tar in zip(out_test, out_test_label):
    i += 1
    if i > minimum:
        break
    tr, pred_probs = translator.translate(ten, True)
    indices = translate_and_get_indices(tr, tar, pred_probs)
    out_train_indices.append(np.mean(indices))


x_train = np.concatenate([in_train_indices, out_train_indices])
y_train = [1. for _ in range(len(in_train_indices))]
y_train.extend([0. for _ in range(len(out_train_indices))])

x_test = np.concatenate([in_test_indices, out_train_indices])
y_test = [1. for _ in range(len(in_train_indices))]
y_test.extend([0. for _ in range(len(out_train_indices))])

clf = svm.SVC()
clf.fit(x_train.reshape(-1, 1), y_train)
y_pred = clf.predict(x_test.reshape(-1, 1))
print("Attack 1 Accuracy : %.2f%%" % (100.0 * accuracy_score(y_test, y_pred)))
