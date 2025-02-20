import json
import os

import numpy as np
import pandas as pd
import tensorflow.keras.backend as K
from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from tqdm import tqdm

from model import get_model, get_kd_model
from utils import get_mixup

if __name__ == "__main__":
    file_path_source = "baseline.h5"
    file_path_kd = "kd.h5"
    n_class = 5

    df_train = pd.read_csv("../input/mitbih_train.csv", header=None)
    df = pd.read_csv("../input/mitbih_test.csv", header=None)

    df_test, df_val = train_test_split(df, test_size=0.2, random_state=1337)

    Y_train = np.array(df_train[187].values).astype(np.int8)
    X_train = np.array(df_train[list(range(187))].values)[..., np.newaxis]
    Y_train = np.eye(n_class)[Y_train]

    Y_val = np.array(df_val[187].values).astype(np.int8)
    X_val = np.array(df_val[list(range(187))].values)[..., np.newaxis]
    Y_val = np.eye(n_class)[Y_val]

    Y_test = np.array(df_test[187].values).astype(np.int8)
    X_test = np.array(df_test[list(range(187))].values)[..., np.newaxis]

    model_source = get_model()
    model_source.load_weights(file_path_source)
    Y_train_pred = model_source.predict(X_train)
    Y_val_pred = model_source.predict(X_val)

    model = get_kd_model()

    checkpoint = ModelCheckpoint(
        file_path_kd, monitor="val_loss", verbose=1, save_best_only=True, mode="min"
    )
    reduce = ReduceLROnPlateau(monitor="val_loss", patience=10, min_lr=1e-7, mode="min")
    early = EarlyStopping(monitor="val_loss", patience=30, mode="min")

    for i in tqdm(range(300)):
        X_new, Y_new = get_mixup(X_train, Y_train_pred)
        model.fit(
            X_train,
            Y_train,
            validation_data=(X_val, Y_val_pred),
            epochs=2,
            verbose=2,
            callbacks=[checkpoint, reduce, early],
            batch_size=64,
        )
        if i == 60:
            K.set_value(model.optimizer.lr, 0.000001)

    model.load_weights(file_path_kd)

    pred_test = model.predict(X_test)
    pred_test = np.argmax(pred_test, axis=-1)

    f1 = f1_score(Y_test, pred_test, average="macro")

    acc = accuracy_score(Y_test, pred_test)

    print("acc :", acc)
    print("f1 :", f1)

    rnd = np.random.randint(1, 100000)
    os.makedirs("../output/ecg/", exist_ok=True)

    with open("../output/ecg/kd_performance_%s.json" % int(rnd), "w") as f:
        json.dump({"acc": acc, "f1": f1}, f, indent=4)
