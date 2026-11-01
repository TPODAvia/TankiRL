import pytest


@pytest.mark.integration
def test_real_game():
    from tankirl.evaluation.check_game import run

    run()


@pytest.mark.integration
def test_gymnasium():
    from gymnasium.utils.env_checker import check_env
    from tankirl.envs.tanki_env import TankiEnv

    env = TankiEnv({"stage": 1, "frame_stack": 1})
    try:
        check_env(env, skip_render_check=True, skip_close_check=True)
    finally:
        env.close()
