import numpy as np

NVECS = [3, 3, 3, 2]
KEYS = {"KeyW", "KeyS", "KeyA", "KeyD", "KeyZ", "KeyX", "KeyC", "Space"}


def action_keys(action):
    a = np.asarray(action)
    if (
        a.shape != (4,)
        or not np.all(a == a.astype(int))
        or np.any(a < 0)
        or np.any(a >= NVECS)
    ):
        raise ValueError(f"Invalid MultiDiscrete action: {action}")
    keys = {
        ("KeyS", None, "KeyW")[int(a[0])],
        ("KeyA", None, "KeyD")[int(a[1])],
        ("KeyZ", None, "KeyX")[int(a[2])],
    }
    if a[3]:
        keys.add("Space")
    return keys - {None}


def keys_action(keys):
    k = set(keys)
    return np.array(
        [
            1 + int("KeyW" in k) - int("KeyS" in k),
            1 + int("KeyD" in k) - int("KeyA" in k),
            1 + int("KeyX" in k) - int("KeyZ" in k),
            int("Space" in k),
        ],
        dtype=np.int64,
    )
