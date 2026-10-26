from triage_gym import ERTriageEnv
import numpy as np

def run_simulation():
    env = ERTriageEnv()
    obs, _ = env.reset()

    total_score = 0

    print("--- Starting ER Triage Simulation ---")
    for step in range(15):
        print(f"\nStep {step + 1}")
        print(f"Waiting Room Queue: {obs}")

        action = int(np.argmax(obs))

        print(f"Software admits Patient Slot {action} (Severity {obs[action]})")

        obs, reward, terminated, truncated, _ = env.step(action)
        total_score += reward

        print(f"Points awarded: {reward} | Total Score: {total_score}")

if __name__ == "__main__":
    run_simulation()
