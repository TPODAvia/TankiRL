from types import SimpleNamespace
import itertools
import numpy as np
import pytest
from tankirl.game_bridge.actions import action_keys, keys_action
from tankirl.agents.p2p_agent import MouseTurretAdapter
from tankirl.game_bridge.rewards import Rewards


def test_action_roundtrip_and_no_conflicts():
    for a in itertools.product(range(3), range(3), range(3), range(2)):
        keys = action_keys(a)
        assert not {"KeyW", "KeyS"} <= keys
        assert not {"KeyA", "KeyD"} <= keys
        assert not {"KeyZ", "KeyX"} <= keys
        assert np.array_equal(keys_action(keys), a)


@pytest.mark.parametrize("a", [[-1, 1, 1, 0], [1, 1, 1, 2], [1, 1, 1], [1.5, 1, 1, 0]])
def test_invalid_action(a):
    with pytest.raises(ValueError):
        action_keys(a)


def test_mouse_deadzone_and_cap():
    adapter = MouseTurretAdapter()
    a, d = adapter.translate(
        SimpleNamespace(keys=["w"], mouse_buttons=["0"], mouse_delta_x=1)
    )
    assert list(a) == [2, 1, 1, 1] and d == 0
    a, d = adapter.translate(
        SimpleNamespace(keys=[], mouse_buttons=[], mouse_delta_x=-1000)
    )
    assert a[2] == 0 and d == 0.1


def telemetry(x=0, t=0, damage=0):
    return dict(
        time_ms=t,
        damage_dealt=damage,
        damage_received=0,
        hits=0,
        kills=0,
        deaths=0,
        actors=[dict(local=True, position=dict(x=x, y=0, z=0))],
    )


def test_no_reward_for_firing_or_spinning():
    rewards = Rewards()
    rewards.reset(telemetry())
    total = 0
    for i in range(200):
        r, _ = rewards.update(telemetry(t=i * 100), [1, 2, 2, 1])
        total += r
    assert total <= 0.005


def test_exploration_is_bounded_and_damage_counts_once():
    rewards = Rewards()
    rewards.reset(telemetry())
    bonus = 0
    for i in range(1000):
        _, terms = rewards.update(telemetry(x=i * 400, t=i * 100), [2, 1, 1, 0])
        bonus += terms["exploration"]
    assert bonus <= 0.2000001
    _, terms = rewards.update(telemetry(x=400000, t=100000, damage=50), [1, 1, 1, 1])
    assert terms["damage_dealt"] == 50
    _, terms = rewards.update(telemetry(x=400000, t=100100, damage=50), [1, 1, 1, 1])
    assert terms["damage_dealt"] == 0


def test_aim_reward_cannot_be_farmed_by_oscillation():
    r = Rewards()
    r.reset(telemetry() | {"aim_alignment": 0.2})
    total = 0
    for i in range(100):
        _, terms = r.update(
            telemetry(t=i * 100) | {"aim_alignment": 1.0 if i % 2 else 0.0},
            [1, 1, 0, 0],
        )
        total += terms["aim_improvement"]
    assert total == pytest.approx(0.16)
