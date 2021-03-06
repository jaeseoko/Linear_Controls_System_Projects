import numpy as np

class EKF_SLAM():
    def __init__(self, init_mu, init_P, dt, W, V, n):
        """Initialize EKF SLAM

        Create and initialize an EKF SLAM to estimate the robot's pose and
        the location of map features

        Args:
            init_mu: A numpy array of size (3+2*n, ). Initial guess of the mean 
            of state. 
            init_P: A numpy array of size (3+2*n, 3+2*n). Initial guess of 
            the covariance of state.
            dt: A double. The time step.
            W: A numpy array of size (3+2*n, 3+2*n). Process noise
            V: A numpy array of size (2*n, 2*n). Observation noise
            n: A int. Number of map features
            

        Returns:
            An EKF SLAM object.
        """
        self.mu = init_mu  # initial guess of state mean
        self.P = init_P  # initial guess of state covariance
        self.dt = dt  # time step
        self.W = W  # process noise 
        self.V = V  # observation noise
        self.n = n  # number of map features


    def _f(self, x, u):
        """Non-linear dynamic function.

        Compute the state at next time step according to the nonlinear dynamics f.

        Args:
            x: A numpy array of size (3+2*n, ). State at current time step.
            u: A numpy array of size (3, ). The control input [\dot{x}, \dot{y}, \dot{\psi}]

        Returns:
            x_next: A numpy array of size (3+2*n, ). The state at next time step
        """
        x_next = x
        # x_next = x
        x_next[0] = x[0] + self.dt*(u[0]*np.cos(x[2])-u[1]*np.sin(x[2]))
        x_next[1] = x[1] + self.dt*(u[0]*np.sin(x[2])+u[1]*np.cos(x[2]))
        x_next[2] = self._wrap_to_pi(x[2] + self.dt*u[2])
        # x_next[2] = x[2] + self.dt*u[2]

        # for i in range(3,2*self.n):
        #     x_next[i+3] = x[i+3]

        # x_next += self.W[0:3+2*self.n][0]    

        return x_next


    def _h(self, x):
        """Non-linear measurement function.

        Compute the sensor measurement according to the nonlinear function h.

        Args:
            x: A numpy array of size (3+2*n, ). State at current time step.

        Returns:
            y: A numpy array of size (2*n, ). The sensor measurement.
        """
        y = np.zeros((2*self.n))
        for i in range(0,self.n):
            y[i] = np.sqrt((x[2*i+3]-x[0])**2 + (x[2*i+4]-x[1])**2)
            y[self.n+i] = self._wrap_to_pi(np.arctan2(x[2*i+4]-x[1],x[2*i+3]-x[0]) - x[2])
        
        # y += self.V[0:2*self.n][0]    

        return y


    def _compute_F(self, u):
        """Compute Jacobian of f
        
        You will use self.mu in this function.

        Args:
            u: A numpy array of size (3, ). The control input [\dot{x}, \dot{y}, \dot{\psi}]

        Returns:
            F: A numpy array of size (3+2*n, 3+2*n). The jacobian of f evaluated at x_k.
        """
        F = np.eye(3+2*self.n)
        F[0][2] = -self.dt*(np.sin(self.mu[2])*u[0] + np.cos(self.mu[2])*u[1])
        F[1][2] = self.dt*(np.cos(self.mu[2])*u[0] - np.sin(self.mu[2])*u[1])

        return F


    def _compute_H(self):
        """Compute Jacobian of h
        
        You will use self.mu in this function.

        Args:

        Returns:
            H: A numpy array of size (2*n, 3+2*n). The jacobian of h evaluated at x_k.
        """
        H = np.zeros((2*self.n,3+2*self.n))
        for i in range(0,self.n):


            # ************** distance sensor ************** #
            # Left upper quad
            H[i][0] = (self.mu[0] - self.mu[2*i+3])/ \
                np.sqrt(((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2))
            H[i][1] = (self.mu[1] - self.mu[2*i+4])/ \
                np.sqrt(((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2))

            # Right upper quad
            H[i][3+ 2*i] = (self.mu[2*i+3] - self.mu[0])/ \
                np.sqrt(((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2))
            H[i][4+ 2*i] = (self.mu[2*i+4] - self.mu[1])/ \
                np.sqrt(((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2))


            # ************** bearing sensor ************** #
            # Left lower quad
            H[i+self.n][0] = -(self.mu[1] - self.mu[2*i+4])/ \
                ((self.mu[2*i + 3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2)
            H[i+self.n][1] = -(self.mu[2*i+3] - self.mu[0])/ \
                ((self.mu[2*i + 3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2)
            H[i+self.n][2] = -1

            # Right lower quad
            H[i+self.n][3 + 2*i] = -(self.mu[2*i+4]- self.mu[1])/ \
                ((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2)
            H[i+self.n][4 + 2*i] = -(self.mu[0] - self.mu[2*i+3])/ \
                ((self.mu[2*i+3] - self.mu[0])**2 + (self.mu[2*i+4] - self.mu[1])**2)    

        return H


    def predict_and_correct(self, y, u):
        """Predice and correct step of EKF.
        
        You will use self.mu in this function. You must update self.mu in this function.

        Args:
            y: A numpy array of size (2*n, ). The measurements according to the project description.
            u: A numpy array of size (3, ). The control input [\dot{x}, \dot{y}, \dot{\psi}]

        Returns:
            self.mu: A numpy array of size (3+2*n, ). The corrected state estimation
            self.P: A numpy array of size (3+2*n, 3+2*n). The corrected state covariance
        """

        # compute F and H matrix
        F = self._compute_F(u)
        H = self._compute_H()
        
        # last_mu = self.mu
        #***************** Predict step *****************#
        # predict the state
        x_predict = self._f(self.mu,u)
        
        # predict the error covariance
        # P = np.cov(x_predict,self.mu)
        P = F@self.P@F.T + self.W

        #***************** Correct step *****************#
        # compute the Kalman gain
        L = P@H.T@np.linalg.inv(H@P@H.T + self.V)

        h = self._h(x_predict)
        y_h = y-h

        for i in range(self.n,2*self.n):
            y_h[i] = self._wrap_to_pi(y_h[i])

            # print(y_h[i])
        
        
        
        # update estimation with new measurement
        new_mu = x_predict + L@(y_h)
        new_mu[2] = self._wrap_to_pi(new_mu[2])
        self.mu = new_mu
        # update the error covariance
        self.P = (np.eye(3+2*self.n) - L@H)@P
        return self.mu, self.P


    def _wrap_to_pi(self, angle):
        angle = angle - 2*np.pi*np.floor((angle+np.pi )/(2*np.pi))
        
        return angle


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    m = np.array([[0.,  0.],
                  [0.,  20.],
                  [20., 0.],
                  [20., 20.],
                  [0,  -20],
                  [-20, 0],
                  [-20, -20],
                  [-50, -50]]).reshape(-1)

    dt = 0.01
    T = np.arange(0, 20, dt)
    n = int(len(m)/2)
    W = np.zeros((3+2*n, 3+2*n))
    W[0:3, 0:3] = dt**2 * 1 * np.eye(3)
    V = 0.1*np.eye(2*n)
    V[n:,n:] = 0.01*np.eye(n)

    # EKF estimation
    mu_ekf = np.zeros((3+2*n, len(T)))
    mu_ekf[0:3,0] = np.array([2.2, 1.8, 0.])
    # mu_ekf[3:,0] = m + 0.1
    mu_ekf[3:,0] = m + np.random.multivariate_normal(np.zeros(2*n), 0.5*np.eye(2*n))
    init_P = 1*np.eye(3+2*n)

    # initialize EKF SLAM
    slam = EKF_SLAM(mu_ekf[:,0], init_P, dt, W, V, n)
    
    # real state
    mu = np.zeros((3+2*n, len(T)))
    mu[0:3,0] = np.array([2, 2, 0.])
    mu[3:,0] = m

    y_hist = np.zeros((2*n, len(T)))
    for i, t in enumerate(T):
        if i > 0:
            # real dynamics
            u = [-5, 2*np.sin(t*0.5), 1*np.sin(t*3)]
            # u = [0.5, 0.5*np.sin(t*0.5), 0]
            # u = [0.5, 0.5, 0]
            
            mu[:,i] = slam._f(mu[:,i-1], u) + \
                np.random.multivariate_normal(np.zeros(3+2*n), W)

            # measurements
            y = slam._h(mu[:,i]) + np.random.multivariate_normal(np.zeros(2*n), V)
            y_hist[:,i] = (y-slam._h(slam.mu))
            # apply EKF SLAM
            mu_est, _ = slam.predict_and_correct(y, u)
            mu_ekf[:,i] = mu_est


    plt.figure(1, figsize=(10,6))
    plt.suptitle("Ground Truth and Estimates")
    ax1 = plt.subplot(121, aspect='equal')
    ax1.plot(mu[0,:], mu[1,:], 'b')
    ax1.plot(mu_ekf[0,:], mu_ekf[1,:], 'r--')
    mf = m.reshape((-1,2))
    ax1.scatter(mf[:,0], mf[:,1])
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')

    ax2 = plt.subplot(322)
    ax2.plot(T, mu[0,:], 'b')
    ax2.plot(T, mu_ekf[0,:], 'r--')
    ax2.set_xlabel('t')
    ax2.set_ylabel('X')

    ax3 = plt.subplot(324)
    ax3.plot(T, mu[1,:], 'b')
    ax3.plot(T, mu_ekf[1,:], 'r--')
    ax3.set_xlabel('t')
    ax3.set_ylabel('Y')

    ax4 = plt.subplot(326)
    ax4.plot(T, mu[2,:], 'b')
    ax4.plot(T, mu_ekf[2,:], 'r--')
    ax4.set_xlabel('t')
    ax4.set_ylabel('psi')
    
    plt.savefig("Estimate_Plot")

    plt.figure(2)
    plt.suptitle("Noise Plot")
    ax1 = plt.subplot(211)
    ax1.plot(T, y_hist[0:n, :].T)
    ax2 = plt.subplot(212)
    ax2.plot(T, y_hist[n:, :].T)
    
    plt.savefig("Noise_Plot")

    plt.show()
