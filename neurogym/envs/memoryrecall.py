"""A generic memory recall task."""

from collections import OrderedDict
import numpy as np

from gym import spaces
import neurogym as ngym
from neurogym.ops import tasktools


class MemoryRecall(ngym.Env):
    # TODO: Need to be made more general by passing the memories
    def __init__(
            self,
            dt=1,
            stim_dim=10,
            store_signal_dim=1,
            T_min=15,
            T_max=25,
            T_distribution='uniform',
            p_recall=0.1,
            chance=0.7,
            balanced=True,
            **kwargs,
    ):
        """
        Args:
            stim_dim: int, stimulus dimension
            store_signal_dim: int, storage signal dimension
            T: int, sequence length
            p_recall: proportion of patterns stored for recall
            chance: chance level performance
        """
        super(MemoryRecall, self).__init__(dt=dt)

        self.stim_dim = stim_dim
        self.store_signal_dim = store_signal_dim
        self.input_dim = self.stim_dim + self.store_signal_dim
        self.output_dim = stim_dim
        self.T_min = T_min
        if T_max is None:
            self.T_max = T_min
        else:
            self.T_max = T_max
        assert self.T_max >= self.T_min, 'T_max must be larger than T_min'
        self.T_distribution = T_distribution
        if T_distribution == 'uniform':
            self.generate_T = lambda : np.random.randint(self.T_min, self.T_max+1)
        else:
            raise ValueError('Not supported T distribution type', str(T_distribution))
        self.p_recall = p_recall
        self.balanced = balanced
        self.chance = chance
        if self.balanced:
            self.p_unknown = (1 - chance) * 2.
        else:
            # p_flip: amount of sensory noise during recall
            self.p_flip = 1 - chance

        if p_recall > 0.5:
            print('Cannot have p_recall larger than 0.5')

        # Environment specific
        self.action_space = spaces.Box(-np.inf, np.inf, shape=(stim_dim,),
                                       dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(stim_dim,),
                                       dtype=np.float32)

    def __str__(self):
        print('Recall dataset:')
        nicename_dict = OrderedDict(
            [('stim_dim', 'Stimulus dimension'),
             ('store_signal_dim', 'Storage signal dimension'),
             ('input_dim', 'Input dimension'),
             ('output_dim', 'Output dimension'),
             ('T_min', 'Minimum sequence length'),
             ('T_max', 'Maximum sequence length'),
             ('T_distribution', 'Sequence length distribution'),
             ('p_recall', 'Proportion of recall'),
             ('chance', 'Chancel level accuracy')
             ]
        )
        if self.balanced:
            nicename_dict['p_unknown'] = 'Proportion of unknown elements at recall'
        else:
            nicename_dict['p_flip'] = 'Proportion of flipping at recall'

        string = ''
        for key, name in nicename_dict.items():
            string += name +' : ' + str(getattr(self, key)) + '\n'
        return string

    def new_trial(self):
        stim_dim = self.stim_dim

        T = self.generate_T()

        T_recall = int(self.p_recall * T)
        T_store = T - T_recall

        X_stim = np.zeros((T, stim_dim))
        X_store_signal = np.zeros((T, 1))
        Y = np.zeros((T, stim_dim))
        M = np.zeros(T)

        # Storage phase
        if self.balanced:
            X_stim[:T_store, :] = (np.random.rand(T_store, stim_dim) > 0.5) * 2.0 - 1.0
        else:
            X_stim[:T_store, :] = (np.random.rand(T_store, stim_dim) > 0.5) * 1.0

        store_signal = np.random.choice(np.arange(T_store), T_recall,
                                        replace=False)
        X_store_signal[store_signal, 0] = 1.

        # Recall phase
        X_stim_recall = X_stim[store_signal]
        Y[T_store:, :] = X_stim_recall
        M[T_store:] = 1.

        # Perturb X_stim_recall
        # Flip probability
        if self.balanced:
            known_matrix = (np.random.rand(T_recall, stim_dim) > self.p_unknown) * 1.0
            X_stim[T_store:, :stim_dim] = X_stim_recall * known_matrix
        else:
            flip_matrix = np.random.rand(T_recall, stim_dim) < self.p_flip
            X_stim[T_store:, :stim_dim] = X_stim_recall * (1 - flip_matrix) + (
                        1 - X_stim_recall) * flip_matrix

        X = np.concatenate((X_stim, X_store_signal), axis=1)

        self.obs = X
        self.gt = Y
        self.mask = M
        self.tmax = T * self.dt
        self.t = 0

        return X, Y, M

    def _step(self, action):
        # ---------------------------------------------------------------------
        # Reward and observations
        # ---------------------------------------------------------------------
        ind = int(self.t / self.dt)
        print(self.tmax)
        print(self.t)
        obs = self.obs[ind, :]
        gt = self.gt[ind]
        reward = np.mean(abs(gt - action)) * self.mask[ind]
        # ---------------------------------------------------------------------
        # new trial?
        new_trial = self.t >= self.tmax - self.dt

        self.t += self.dt

        done = False

        return obs, reward, done, {'new_trial': new_trial, 'gt': gt}

    def step(self, action):
        obs, reward, done, info = self._step(action)
        if info['new_trial']:
            self.new_trial()
        return obs, reward, done, info
