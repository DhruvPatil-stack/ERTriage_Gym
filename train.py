from stable_baselines3 import PPO
from triage_gym import ERTriageEnv

env = ERTriageEnv()

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    n_steps=1024,
    batch_size=128,
    n_epochs=15,
    learning_rate=2.5e-4,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01,
)

print("Training started — 500,000 timesteps...")
model.learn(total_timesteps=500_000)
model.save("triage_ppo")
print("Model saved to triage_ppo.zip")
