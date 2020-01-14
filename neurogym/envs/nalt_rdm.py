#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 17:39:17 2019

@author: molano


Perceptual decision-making task, based on

  Bounded integration in parietal cortex underlies decisions even when viewing
  duration is dictated by the environment.
  R Kiani, TD Hanks, & MN Shadlen, JNS 2008.

  http://dx.doi.org/10.1523/JNEUROSCI.4761-07.2008

  But allowing for more than 2 choices.

"""

import numpy as np
from gym import spaces
import neurogym as ngym
from neurogym.ops import tasktools


def get_default_timing():
    return {'fixation': ('constant', 500),
            'stimulus': ('truncated_exponential', [330, 80, 1500]),
            'decision': ('constant', 500)}


class nalt_RDM(ngym.EpochEnv):
    def __init__(self, dt=100, timing=None, stimEv=1., n_ch=3, **kwargs):
        super().__init__(dt=dt)
        self.n = n_ch
        self.choices = np.arange(n_ch) + 1
        # cohs specifies the amount of evidence (which is modulated by stimEv)
        self.cohs = np.array([0, 6.4, 12.8, 25.6, 51.2])*stimEv
        # Input noise
        self.sigma = np.sqrt(2*100*0.01)
        self.sigma_dt = self.sigma / np.sqrt(self.dt)

        default_timing = get_default_timing()
        if timing is not None:
            default_timing.update(timing)
        self.set_epochtiming(default_timing)

        # Rewards
        self.R_ABORTED = -0.1
        self.R_CORRECT = +1.
        self.R_FAIL = 0.
        self.R_MISS = 0.
        self.abort = False
        # action and observation spaces
        self.action_space = spaces.Discrete(n_ch+1)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(n_ch+1,),
                                            dtype=np.float32)

    def new_trial(self, **kwargs):
        """
        new_trial() is called when a trial ends to generate the next trial.
        The following variables are created:
            durations, which stores the duration of the different periods (in
            the case of rdm: fixation, stimulus and decision periods)
            ground truth: correct response for the trial
            coh: stimulus coherence (evidence) for the trial
            obs: observation
        """
        # ---------------------------------------------------------------------
        # Epochs
        # ---------------------------------------------------------------------
        self.add_epoch('fixation', after=0)
        self.add_epoch('stimulus', after='fixation')
        self.add_epoch('decision', after='stimulus', last_epoch=True)
        # ---------------------------------------------------------------------
        # Trial
        # ---------------------------------------------------------------------
        if 'gt' in kwargs.keys():
            ground_truth = kwargs['gt']
        else:
            ground_truth = self.rng.choice(self.choices)
        if 'coh' in kwargs.keys():
            coh = kwargs['coh']
        else:
            coh = self.rng.choice(self.cohs)

        self.ground_truth = ground_truth
        self.coh = coh

        self.set_ob('fixation', [1] + [0]*self.n)
        stimulus_value = [1] + [(1 - coh/100)/2] * self.n
        stimulus_value[ground_truth] = (1 + coh/100)/2
        self.set_ob('stimulus', stimulus_value)
        self.obs[self.stimulus_ind0:self.stimulus_ind1, 1:] +=\
            np.random.randn(self.stimulus_ind1-self.stimulus_ind0, self.n) * self.sigma_dt

        self.set_groundtruth('fixation', 0)
        self.set_groundtruth('stimulus', 0)
        self.set_groundtruth('decision', ground_truth)

    def _step(self, action, **kwargs):
        """
        _step receives an action and returns:
            a new observation, obs
            reward associated with the action, reward
            a boolean variable indicating whether the experiment has end, done
            a dictionary with extra information:
                ground truth correct response, info['gt']
                boolean indicating the end of the trial, info['new_trial']
        """
        # ---------------------------------------------------------------------
        # Reward and observations
        # ---------------------------------------------------------------------
        new_trial = False

        obs = self.obs_now
        gt = self.gt_now

        reward = 0
        if self.in_epoch('fixation'):
            if action != 0:
                new_trial = self.abort
                reward = self.R_ABORTED
        elif self.in_epoch('decision'):
            if action != 0:
                new_trial = True
                if action == gt:
                    reward = self.R_CORRECT
                else:
                    reward = self.R_FAIL

        return obs, reward, False, {'new_trial': new_trial, 'gt': gt}



if __name__ == '__main__':
    env = nalt_RDM()
    tasktools.plot_struct(env)