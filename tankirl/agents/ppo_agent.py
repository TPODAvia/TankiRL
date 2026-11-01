from stable_baselines3 import PPO


def make_ppo(env, config):
    return PPO(
        "CnnPolicy",
        env,
        n_steps=config["n_steps"],
        batch_size=config["batch_size"],
        n_epochs=config["n_epochs"],
        learning_rate=config["learning_rate"],
        device=config["device"],
        seed=config["seed"],
        tensorboard_log="logs/tensorboard",
        verbose=1,
        policy_kwargs={"features_extractor_kwargs": {"features_dim": 128}},
    )
