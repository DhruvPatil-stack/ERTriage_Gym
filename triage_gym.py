import gymnasium as gym
from gymnasium import spaces
import numpy as np

class ERTriageEnv(gym.Env):
    def __init__(self):
        super(ERTriageEnv, self).__init__()
        # obs: [sev0..4, wait0..4] — agent can see both severity and wait times
        self.observation_space = spaces.Box(low=0, high=10, shape=(10,), dtype=np.float32)
        self.action_space = spaces.Discrete(5)
        self.max_steps = 100
        self._init_state()

    def _init_state(self):
        self.state = np.random.randint(1, 6, size=5, dtype=np.int32)
        self.wait_times = np.zeros(5, dtype=np.int32)
        self.sev5_untreated_steps = np.zeros(5, dtype=np.int32)
        self.current_step = 0

    def _get_obs(self):
        return np.concatenate([self.state.astype(np.float32), self.wait_times.astype(np.float32)])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._init_state()
        return self._get_obs(), {}

    def step(self, action):
        action = int(action)
        chosen_severity = self.state[action]
        reward = 0

        # Base reward
        if chosen_severity == 5:
            reward += 10
        elif chosen_severity == 4:
            reward += 5
        elif chosen_severity == 3:
            reward += 2
        elif chosen_severity == 1 and np.max(self.state) > 2:
            reward -= 20

        # Deterioration penalty: sev 4/5 waiting > 3 steps
        for i in range(5):
            if self.state[i] >= 4 and self.wait_times[i] >= 3:
                reward -= 5

        # Urgency penalty: sev-5 left untreated > 2 steps
        for i in range(5):
            if self.state[i] == 5 and self.sev5_untreated_steps[i] > 2:
                reward -= 10

        # Replace admitted patient
        self.state[action] = np.random.randint(1, 6)
        self.wait_times += 1
        self.wait_times[action] = 0

        # Escalate severity: each patient has a 15% chance of worsening each step
        for i in range(5):
            if i != action and self.state[i] < 5 and np.random.random() < 0.15:
                self.state[i] = min(5, self.state[i] + 1)

        # Track sev-5 untreated steps
        for i in range(5):
            if self.state[i] == 5:
                self.sev5_untreated_steps[i] += 1
            else:
                self.sev5_untreated_steps[i] = 0
        self.sev5_untreated_steps[action] = 0

        self.current_step += 1
        terminated = False
        truncated = bool(self.current_step >= self.max_steps)

        return self._get_obs(), float(reward), terminated, truncated, {}
