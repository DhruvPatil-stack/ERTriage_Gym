from stable_baselines3 import PPO
from triage_gym import ERTriageEnv
import numpy as np

EPISODES = 50

def run_dummy(episodes):
    env = ERTriageEnv()
    scores, sev1_picks, sev5_delayed = [], 0, 0

    for _ in range(episodes):
        obs, _ = env.reset()
        episode_reward = 0
        for _ in range(100):
            severities = obs[:5].astype(int)
            action = int(np.argmax(severities))
            if severities[action] == 1 and np.max(severities) > 2:
                sev1_picks += 1
            if severities[action] != 5 and 5 in severities:
                sev5_delayed += 1
            obs, reward, _, truncated, _ = env.step(action)
            episode_reward += reward
            if truncated:
                break
        scores.append(episode_reward)

    return scores, sev1_picks, sev5_delayed

def run_trained(episodes):
    env = ERTriageEnv()
    model = PPO.load("triage_ppo")
    scores, sev1_picks, sev5_delayed = [], 0, 0

    for _ in range(episodes):
        obs, _ = env.reset()
        episode_reward = 0
        for _ in range(100):
            severities = obs[:5].astype(int)
            action, _ = model.predict(obs, deterministic=True)
            action = int(action)
            if severities[action] == 1 and np.max(severities) > 2:
                sev1_picks += 1
            if severities[action] != 5 and 5 in severities:
                sev5_delayed += 1
            obs, reward, _, truncated, _ = env.step(action)
            episode_reward += reward
            if truncated:
                break
        scores.append(episode_reward)

    return scores, sev1_picks, sev5_delayed

print(f"Evaluating over {EPISODES} episodes each...\n")

dummy_scores, dummy_sev1, dummy_sev5 = run_dummy(EPISODES)
trained_scores, trained_sev1, trained_sev5 = run_trained(EPISODES)

d_avg = np.mean(dummy_scores)
t_avg = np.mean(trained_scores)
improvement = ((t_avg - d_avg) / abs(d_avg)) * 100

print("=" * 52)
print(f"{'Metric':<34} {'Dummy':>8} {'PPO':>8}")
print("=" * 52)
print(f"{'Avg reward / episode':<34} {d_avg:>8.1f} {t_avg:>8.1f}")
print(f"{'Min reward':<34} {np.min(dummy_scores):>8.1f} {np.min(trained_scores):>8.1f}")
print(f"{'Max reward':<34} {np.max(dummy_scores):>8.1f} {np.max(trained_scores):>8.1f}")
print(f"{'Std deviation':<34} {np.std(dummy_scores):>8.1f} {np.std(trained_scores):>8.1f}")
print(f"{'Bad sev-1 picks (total)':<34} {dummy_sev1:>8} {trained_sev1:>8}")
print(f"{'Sev-5 skipped when present (total)':<34} {dummy_sev5:>8} {trained_sev5:>8}")
print("=" * 52)
print(f"\nPPO improvement over dummy: {improvement:+.1f}%")
