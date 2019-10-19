import numpy as np
import gym_auv.utils.state_space_3d_cor as ss
import gym_auv.utils.geomutils as geom
import matplotlib.pyplot as plt

from gym_auv.utils.current import Current
from mpl_toolkits.mplot3d import Axes3D


class AUV3D():
    def __init__(self, t_step_size, init_state, width=2):
        eta_0 = init_state
        nu_r_0 = np.zeros((6,))
        self.state = np.hstack([eta_0, nu_r_0])
        self.state_trajectory = np.hstack(self.state)

        self.input = np.zeros((3,))
        self.input_trajectory = np.hstack([self.input])
        
        self.t_step_size = t_step_size
        self.width = width
        
        self.current = Current(mu=0.02, Vmin=0.2, Vmax=0.0, Vc_init=0, alpha_init=0, beta_init=np.pi, t_step_size=t_step_size)
    

    def step(self, action):
        thrust = _surge(action[0])
        rudder_angle = _steer(action[1])
        elevator_angle = _steer(action[2])

        self.input = np.array([thrust, rudder_angle, elevator_angle])
        self._sim()

        self.state_trajectory = np.vstack([self.state_trajectory, self.state])
        self.input_trajectory = np.vstack([self.input_trajectory, self.input])


    def _sim(self):
        self.current.sim()
        eta = self.state[:6]
        nu_r = self.state[6:]
        nu_c = self.current(eta)

        eta_dot = geom.J(eta).dot(nu_r+nu_c)
        nu_r_dot = ss.M_inv().dot(
            ss.B(nu_r).dot(self.input)
            - ss.D(nu_r).dot(nu_r)
            - ss.C(nu_r).dot(nu_r)
            - ss.G(eta))
        state_dot = np.hstack([eta_dot, nu_r_dot])
        self.state += state_dot*self.t_step_size
        self.state[3] = geom.princip(self.state[3])
        self.state[4] = geom.princip(self.state[4])
        self.state[5] = geom.princip(self.state[5])
    
    def plot_path(self):
        x = self.state_trajectory[:, 0]
        y = self.state_trajectory[:, 1]
        z = self.state_trajectory[:, 2]
        
        ax = plt.axes(projection='3d')
        ax.scatter3D(x, y, z)
        return ax

    @property
    def position(self):
        """
        Returns an array holding the position of the AUV in cartesian
        coordinates.
        """
        return self.state[0:3]

    @property
    def path_taken(self):
        """
        Returns an array holding the path of the AUV in cartesian
        coordinates.
        """
        return self.state_trajectory[:, 0:3]

    @property
    def heading(self):
        """
        Returns the heading of the AUV wrt true north.
        """
        return self.state[5]

    @property
    def heading_change(self):
        """
        Returns the change of heading of the AUV wrt true north.
        """
        if len(self.state[5])>=2:
            prev_heading = geom.princip(self.state_trajectory[5,-2])
            heading_change = self.heading - prev_heading
        else:
            heading_change = self.heading
        return heading_change

    @property
    def pitch(self):
        """
        Returns the pitch of the AUV wrt NED.
        """
        return self.state[4]

    @property
    def pitch_change(self):
        """
        Returns the change of pitch of the AUV wrt NED.
        """
        if len(self.state[4])>=2:
            prev_pitch = geom.princip(self.state_trajectory[4,-2])
            pitch_change = self.pitch - prev_pitch
        else:
            pitch_change = self.pitch
        return pitch_change

    @property
    def rudder_change(self):
        """
        Returns the smoothed current rudder change.
        """
        sum_rudder_change = 0
        n_samples = min(10, len(self.input_trajectory[1]))
        for i in range(n_samples):
            sum_rudder_change += self.input_trajectory[1, -1 - i]
        return sum_rudder_change/n_samples

    @property
    def elevator_change(self):
        """
        Returns the smoothed current rudder change.
        """
        sum_elevator_change = 0
        n_samples = min(10, len(self.input_trajectory[2]))
        for i in range(n_samples):
            sum_elevator_change += self.input_trajectory[2, -1 - i]
        return sum_elevator_change/n_samples

    @property
    def velocity(self):
        """
        Returns the surge, sway and heave velocity of the AUV.
        """
        return self.state[6:9]

    @property
    def speed(self):
        """
        Returns the length of the velocity vector of the AUV.
        """
        return np.linalg.norm(self.velocity)

    @property
    def angular_velocity(self):
        """
        Returns the rate of rotation about the NED frame.
        """
        return self.state[9:12]

    @property
    def max_speed(self):
        """
        Returns the max speed of the AUV.
        """
        return ss.U_max

    @property
    def crab_angle(self):
        return np.arctan2(self.velocity[1], self.velocity[0])

    @property
    def course(self):
        return self.heading + self.crab_angle


def _surge(surge):
    surge = np.clip(surge, 0, 1)
    return surge*ss.thrust_max


def _steer(steer):
    steer = np.clip(steer, -1, 1)
    return steer*ss.rudder_max