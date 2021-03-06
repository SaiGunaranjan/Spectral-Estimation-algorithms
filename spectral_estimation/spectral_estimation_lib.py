# -*- coding: utf-8 -*-
"""
Created on Tue Mar 19 21:06:12 2019

@author: Sai Gunaranjan Pelluri
"""
import numpy as np



def sts_correlate(x):
    N= x.shape[1]
    y= np.hstack((x,np.zeros_like(x)))
    xfft=np.fft.fft(y,axis=1)
    corout= np.fft.ifft(xfft*np.conj(xfft),axis=1)[:,0:N]    
    return corout


def vtoeplitz(toprow):

    Npts= toprow.shape[1]
    Nrow= toprow.shape[0]
    
    ACM= np.zeros((Nrow,Npts,Npts)).astype('complex64')
    
    for i in range(Npts):
        ACM[:,i,i:]= toprow[:,0:Npts-i].conj()
        ACM[:,i:,i]= toprow[:,0:Npts-i]
    
    return ACM


def solve_levinson_durbin(toeplitz_matrix, y_vec):
    '''
    Solves for Tx = y
     inputs:
         toeplitz matrix (T): NxN
         y_vec : numpy array of length N
     outputs:
         solution vector x: numpy array of length N
     
        Refer wiki page: https://en.wikipedia.org/wiki/Levinson_recursion # for a simple and elegant understanding and implemenation of the algo
        Refer https://github.com/topisani/OTTO/pull/104/files/c5985545bb39de2a27689066150a5caac0c1fdf9 for the cpp implemenation of the algo
    
    '''
    corr_mat = toeplitz_matrix.copy()
    num_iter = corr_mat.shape[0] # N
    inv_fact = 1/corr_mat[0,0] # 1/t0
    backward_vec = inv_fact
    forward_vec = inv_fact
    x_vec = y_vec[0]*inv_fact # x_vec = y[0]/t0
    for iter_count in np.arange(2,num_iter+1):
        forward_error = np.dot(corr_mat[iter_count-1:0:-1,0],forward_vec) # inner product between the forward vector from previous iteration and a flipped version of the 0th column of the corr_mat 
        backward_error = np.dot(corr_mat[0,1:iter_count],backward_vec) # inner product between the backward vector from previous iteration and the 0th row of the corr_mat 
        error_fact = 1/(1-(backward_error*forward_error))
        prev_iter_forward_vec = forward_vec.copy()
        forward_vec = error_fact*np.append(forward_vec,0) - forward_error*error_fact*np.append(0,backward_vec) # forward vector update
        backward_vec = error_fact*np.append(0,backward_vec) - backward_error*error_fact*np.append(prev_iter_forward_vec,0) # backward vector update
        error_x_vec = np.dot(x_vec,corr_mat[iter_count-1,0:iter_count-1]) # error in the xvector
        x_vec = np.append(x_vec,0) + (y_vec[iter_count-1]-error_x_vec)*backward_vec # x_vec update
        
    return x_vec

def solve_levinson_durbin_ymatrix(toeplitz_matrix, y_vector):
    '''
    Solves for Tx = y
     inputs:
         toeplitz matrix (T): NxN
         y_vec : numpy array of shape N x M : M is the number of different y's
     outputs:
         solution vector x: numpy array of length N
     
        Refer wiki page: https://en.wikipedia.org/wiki/Levinson_recursion # for a simple and elegant understanding and implemenation of the algo
        Refer https://github.com/topisani/OTTO/pull/104/files/c5985545bb39de2a27689066150a5caac0c1fdf9 for the cpp implemenation of the algo
    
    '''
    corr_mat = toeplitz_matrix.copy()
    y_vec = y_vector.copy()
    num_iter = corr_mat.shape[0] # N
    inv_fact = 1/corr_mat[0,0] # 1/t0
    num_sols = y_vec.shape[1]
    x_mat = np.zeros((0,num_iter)).astype('complex64')
    for ele in np.arange(num_sols):
        backward_vec = inv_fact
        forward_vec = inv_fact
        x_vec = y_vec[0,ele]*inv_fact # x_vec = y[0]/t0
        for iter_count in np.arange(2,num_iter+1):
            forward_error = np.dot(corr_mat[iter_count-1:0:-1,0],forward_vec) # inner product between the forward vector from previous iteration and a flipped version of the 0th column of the corr_mat 
            backward_error = np.dot(corr_mat[0,1:iter_count],backward_vec) # inner product between the backward vector from previous iteration and the 0th row of the corr_mat 
            error_fact = 1/(1-(backward_error*forward_error))
            prev_iter_forward_vec = forward_vec.copy()
            forward_vec = error_fact*np.append(forward_vec,0) - forward_error*error_fact*np.append(0,backward_vec) # forward vector update
            backward_vec = error_fact*np.append(0,backward_vec) - backward_error*error_fact*np.append(prev_iter_forward_vec,0) # backward vector update
            error_x_vec = np.dot(x_vec,corr_mat[iter_count-1,0:iter_count-1]) # error in the xvector
            x_vec = np.append(x_vec,0) + (y_vec[iter_count-1,ele]-error_x_vec)*backward_vec # x_vec update
        x_mat = np.vstack((x_mat,x_vec))
    final_x_mat = x_mat.T
    
    return final_x_mat


def music_toeplitz(received_signal, num_sources, digital_freq_grid):
    signal_length = len(received_signal)
    auto_corr_vec = sts_correlate(received_signal.T) # Generate the auto-correlation vector of the same length as the signal
    auto_corr_matrix = vtoeplitz(auto_corr_vec) # Create a toeplitz matrix which is variant of the Auto-correlation matrix
    auto_corr_matrix = auto_corr_matrix[0,:,:]
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    noise_subspace = u[:,num_sources::] # The first # number of sources eigen vectors belong to the signal subspace and the remaining eigen vectors of U belong to the noise subspace which is orthogonal to the signal subspace. Hence pick these eigen vectors
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    GhA = np.matmul(noise_subspace.T.conj(),vandermonde_matrix) #G*A essentially projects the vandermond matrix (which spans the signal subspace) on the noise subspace
    AhG = GhA.conj() # A*G
    AhGGhA = np.sum(AhG*GhA,axis=0) # A*GG*A
    pseudo_spectrum = 1/np.abs(AhGGhA) # Pseudo spectrum
    return pseudo_spectrum


def music_forward(received_signal, num_sources, corr_mat_model_order, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order,corr_mat_model_order)).astype('complex64')
    for ele in np.arange(num_samples-corr_mat_model_order+1): # model order dictates the length of the auto-correlation matrix
        auto_corr_matrix += np.matmul(received_signal[ele:ele+corr_mat_model_order,:],received_signal[ele:ele+corr_mat_model_order,:].T.conj()) # Generate the auto-correlation matrix using the expectation method. here we use the forward filtering i.e. y[0:m], y[1:m+1]...
    auto_corr_matrix = auto_corr_matrix/signal_length # Divide the auto-correlation matrix by the signal length
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    noise_subspace = u[:,num_sources::] # The first # number of sources eigen vectors belong to the signal subspace and the remaining eigen vectors of U belong to the noise subspace which is orthogonal to the signal subspace. Hence pick these eigen vectors
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(corr_mat_model_order),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    GhA = np.matmul(noise_subspace.T.conj(),vandermonde_matrix) #G*A essentially projects the vandermond matrix (which spans the signal subspace) on the noise subspace
    AhG = GhA.conj() # A*G
    AhGGhA = np.sum(AhG*GhA,axis=0) # A*GG*A
    pseudo_spectrum = 1/np.abs(AhGGhA) # Pseudo spectrum
    return pseudo_spectrum

def music_backward(received_signal, num_sources, corr_mat_model_order, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half the signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order,corr_mat_model_order)).astype('complex64')
    for ele in np.arange(corr_mat_model_order-1,signal_length):
        if ele == corr_mat_model_order-1:
            auto_corr_matrix += np.matmul(received_signal[ele::-1,:],received_signal[ele::-1,:].T.conj())
        else:
            auto_corr_matrix += np.matmul(received_signal[ele:ele-corr_mat_model_order:-1,:],received_signal[ele:ele-corr_mat_model_order:-1,:].T.conj())
    auto_corr_matrix = auto_corr_matrix/signal_length # Divide the auto-correlation matrix by the signal length
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    noise_subspace = u[:,num_sources::] # The first # number of sources eigen vectors belong to the signal subspace and the remaining eigen vectors of U belong to the noise subspace which is orthogonal to the signal subspace. Hence pick these eigen vectors
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(corr_mat_model_order),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    GhA = np.matmul(noise_subspace.T.conj(),vandermonde_matrix) #G*A essentially projects the vandermond matrix (which spans the signal subspace) on the noise subspace
    AhG = GhA.conj() # A*G
    AhGGhA = np.sum(AhG*GhA,axis=0) # A*GG*A
    pseudo_spectrum = 1/np.abs(AhGGhA) # Pseudo spectrum
    return pseudo_spectrum

def esprit_toeplitz(received_signal, num_sources):
    signal_length = len(received_signal)
    auto_corr_vec = sts_correlate(received_signal.T) # Generate the auto-correlation vector of the same length as the signal
    auto_corr_matrix = vtoeplitz(auto_corr_vec) # Create a toeplitz matrix which is variant of the Auto-correlation matrix
    auto_corr_matrix = auto_corr_matrix[0,:,:]
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    us = u[:,0:num_sources] # signal subspace
    us1 = us[0:signal_length-1,:] # First N-1 rows of us
    us2 = us[1:signal_length,:] # Last N-1 rows of us
    phi = np.matmul(np.linalg.pinv(us1), us2) # phi = pinv(us1)*us2, phi is similar to D and has same eigen vaues as D. D is a diagonal matrix with elements whose phase is the frequencies
    eig_vals = np.linalg.eigvals(phi) # compute eigen values of the phi matrix which are same as the eigen values of the D matrix since phi and D are similar matrices and hence share same eigen values
    est_freq = np.angle(eig_vals) # Angle/phase of the eigen values gives the frequencies
    return est_freq
    
def esprit_forward(received_signal, num_sources, corr_mat_model_order):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order,corr_mat_model_order)).astype('complex64')
    for ele in np.arange(signal_length-corr_mat_model_order+1): # model order dictates the length of the auto-correlation matrix
        auto_corr_matrix += np.matmul(received_signal[ele:ele+corr_mat_model_order,:],received_signal[ele:ele+corr_mat_model_order,:].T.conj()) # Generate the auto-correlation matrix using the expectation method. here we use the forward filtering i.e. y[0:m], y[1:m+1]...
    auto_corr_matrix = auto_corr_matrix/signal_length # Divide the auto-correlation matrix by the signal length
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    us = u[:,0:num_sources] # signal subspace
    us1 = us[0:corr_mat_model_order-1,:] # First N-1 rows of us
    us2 = us[1:corr_mat_model_order,:] # Last N-1 rows of us
    phi = np.matmul(np.linalg.pinv(us1), us2) # phi = pinv(us1)*us2, phi is similar to D and has same eigen vaues as D. D is a diagonal matrix with elements whose phase is the frequencies
    eig_vals = np.linalg.eigvals(phi) # compute eigen values of the phi matrix which are same as the eigen values of the D matrix since phi and D are similar matrices and hence share same eigen values
    est_freq = np.angle(eig_vals) # Angle/phase of the eigen values gives the frequencies
    return est_freq   

def esprit_backward(received_signal, num_sources, corr_mat_model_order):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order,corr_mat_model_order)).astype('complex64')
    for ele in np.arange(corr_mat_model_order-1,signal_length):
        if ele == corr_mat_model_order-1:
            auto_corr_matrix += np.matmul(received_signal[ele::-1,:],received_signal[ele::-1,:].T.conj())
        else:
            auto_corr_matrix += np.matmul(received_signal[ele:ele-corr_mat_model_order:-1,:],received_signal[ele:ele-corr_mat_model_order:-1,:].T.conj())
    auto_corr_matrix = auto_corr_matrix/signal_length # Divide the auto-correlation matrix by the signal length
    u, s, vh = np.linalg.svd(auto_corr_matrix) # Perform SVD of the Auto-correlation matrix
    us = u[:,0:num_sources] # signal subspace
    us1 = us[0:corr_mat_model_order-1,:] # First N-1 rows of us
    us2 = us[1:corr_mat_model_order,:] # Last N-1 rows of us
    phi = np.matmul(np.linalg.pinv(us1), us2) # phi = pinv(us1)*us2, phi is similar to D and has same eigen vaues as D. D is a diagonal matrix with elements whose phase is the frequencies
    eig_vals = np.linalg.eigvals(phi) # compute eigen values of the phi matrix which are same as the eigen values of the D matrix since phi and D are similar matrices and hence share same eigen values
    est_freq = np.angle(eig_vals) # Angle/phase of the eigen values gives the frequencies
    return est_freq 


def capon_toeplitz(received_signal, digital_freq_grid):
    signal_length = len(received_signal)
    auto_corr_vec = sts_correlate(received_signal.T) # Generate the auto-correlation vector of the same length as the signal
    auto_corr_matrix = vtoeplitz(auto_corr_vec) # Create a toeplitz matrix which is variant of the Auto-correlation matrix
    auto_corr_matrix = auto_corr_matrix[0,:,:]
    auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    auto_corr_matrix_inv_pow_2 = np.matmul(auto_corr_matrix_inv,auto_corr_matrix_inv)
#    filter_bw_beta = corr_mat_model_order + 1
    Ah_Rinv_2_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv_pow_2,vandermonde_matrix),axis=0)
    Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
    filter_bw_beta = Ah_Rinv_2_A/(Ah_Rinv_A)**2
    psd = np.abs((1/(Ah_Rinv_A))/filter_bw_beta)
    return psd

def capon_forward(received_signal, corr_mat_model_order, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order,corr_mat_model_order)).astype('complex64')
    for ele in np.arange(signal_length-corr_mat_model_order+1): # model order dictates the length of the auto-correlation matrix
        auto_corr_matrix += np.matmul(received_signal[ele:ele+corr_mat_model_order,:],received_signal[ele:ele+corr_mat_model_order,:].T.conj()) # Generate the auto-correlation matrix using the expectation method. here we use the forward filtering i.e. y[0:m], y[1:m+1]...
    auto_corr_matrix = auto_corr_matrix/(signal_length-corr_mat_model_order) # Divide the auto-correlation matrix by the (signal length-corr_mat_model_order)
    auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(corr_mat_model_order),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    auto_corr_matrix_inv_pow_2 = np.matmul(auto_corr_matrix_inv,auto_corr_matrix_inv)
    Ah_Rinv_2_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv_pow_2,vandermonde_matrix),axis=0)
    Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
#    filter_bw_beta = Ah_Rinv_2_A/(Ah_Rinv_A)**2
    filter_bw_beta = corr_mat_model_order + 1
    psd = np.abs((1/(Ah_Rinv_A))/filter_bw_beta)
    return psd
    
    
def capon_backward(received_signal, corr_mat_model_order, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order+1,corr_mat_model_order+1)).astype('complex64')
    for ele in np.arange(corr_mat_model_order,signal_length):
        if ele == corr_mat_model_order:
            auto_corr_matrix += np.matmul(received_signal[ele::-1,:],received_signal[ele::-1,:].T.conj())
        else:
            auto_corr_matrix += np.matmul(received_signal[ele:ele-corr_mat_model_order-1:-1,:],received_signal[ele:ele-corr_mat_model_order-1:-1,:].T.conj())
    auto_corr_matrix = auto_corr_matrix/(signal_length-corr_mat_model_order) # Divide the auto-correlation matrix by the (signal length-corr_mat_model_order)
    auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(corr_mat_model_order+1),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    auto_corr_matrix_inv_pow_2 = np.matmul(auto_corr_matrix_inv,auto_corr_matrix_inv)
    Ah_Rinv_2_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv_pow_2,vandermonde_matrix),axis=0)
    Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
    filter_bw_beta = corr_mat_model_order + 1
#    filter_bw_beta = Ah_Rinv_2_A/(Ah_Rinv_A)**2
    psd = np.abs((1/(Ah_Rinv_A))/filter_bw_beta)
    return psd    



def apes(received_signal, corr_mat_model_order, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_matrix = np.zeros((corr_mat_model_order+1,corr_mat_model_order+1)).astype('complex64')
    y_tilda = np.zeros((corr_mat_model_order+1,0)).astype('complex64')
    for ele in np.arange(corr_mat_model_order,signal_length):
        if ele == corr_mat_model_order:
            auto_corr_matrix += np.matmul(received_signal[ele::-1,:],received_signal[ele::-1,:].T.conj())
            y_tilda = np.hstack((y_tilda,received_signal[ele::-1,:]))
        else:
            auto_corr_matrix += np.matmul(received_signal[ele:ele-corr_mat_model_order-1:-1,:],received_signal[ele:ele-corr_mat_model_order-1:-1,:].T.conj())
            y_tilda = np.hstack((y_tilda,received_signal[ele:ele-corr_mat_model_order-1:-1,:]))
    auto_corr_matrix = auto_corr_matrix/(signal_length-corr_mat_model_order) # Divide the auto-correlation matrix by the (signal length-corr_mat_model_order)
    auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
    vandermonde_matrix = np.exp(-1j*np.outer(np.arange(corr_mat_model_order+1),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies
    temp_phasor = np.exp(-1j*np.outer(np.arange(corr_mat_model_order, signal_length),digital_freq_grid))
    G_omega = np.matmul(y_tilda, temp_phasor)/(signal_length-corr_mat_model_order+1)
    Ah_Rinv_G = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv, G_omega),axis=0)
    Gh_Rinv_G = np.sum(G_omega.conj()*np.matmul(auto_corr_matrix_inv, G_omega),axis=0)
    Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
    spectrum = Ah_Rinv_G/((1-Gh_Rinv_G)*Ah_Rinv_A + np.abs(Ah_Rinv_G)**2) # Actual APES based spectrum
#    spectrum = Ah_Rinv_G/Ah_Rinv_A # Capon based spectrum
    
    return spectrum


def iaa_approx_nonrecursive(received_signal, digital_freq_grid):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    auto_corr_vec = sts_correlate(received_signal.T) # Generate the auto-correlation vector of the same length as the signal
    auto_corr_matrix = vtoeplitz(auto_corr_vec) # Create a toeplitz matrix which is variant of the Auto-correlation matrix
    auto_corr_matrix = auto_corr_matrix[0,:,:]    
    auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
    vandermonde_matrix = np.exp(1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies. Notice the posititve sign inside the exponential
    Ah_Rinv_y = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv, received_signal),axis=0)
    Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
#    spectrum = Ah_Rinv_G/((1-Gh_Rinv_G)*Ah_Rinv_A + np.abs(Ah_Rinv_G)**2) # Actual APES based spectrum
    spectrum = Ah_Rinv_y/Ah_Rinv_A 
    
    return spectrum


def iaa_approx_recursive_computeheavy(received_signal, digital_freq_grid, iterations):
    '''corr_mat_model_order : must be strictly less than half the signal length'''
    signal_length = len(received_signal)
    num_freq_grid_points = len(digital_freq_grid)
    spectrum = np.fft.fftshift(np.fft.fft(received_signal.squeeze(),num_freq_grid_points)/(signal_length),axes=(0,))
    vandermonde_matrix = np.exp(1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies. Notice the posititve sign inside the exponential
    for iter_num in np.arange(iterations):
        power_vals = np.abs(spectrum)**2
        diagonal_mat_power_vals = np.diag(power_vals)
        A_P_Ah = np.matmul(vandermonde_matrix,np.matmul(diagonal_mat_power_vals,vandermonde_matrix.T.conj()))
        auto_corr_matrix = A_P_Ah.copy()
        auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
        Ah_Rinv_y = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv, received_signal),axis=0)
        Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
        spectrum = Ah_Rinv_y/Ah_Rinv_A 
    
    return spectrum


def iaa_recursive(received_signal, digital_freq_grid, iterations):
    '''corr_mat_model_order : must be strictly less than half the signal length'''
    signal_length = len(received_signal)
    num_freq_grid_points = len(digital_freq_grid)    
    spectrum = np.fft.fftshift(np.fft.fft(received_signal.squeeze(),num_freq_grid_points)/(signal_length),axes=(0,))
#    spectrum = np.ones(num_freq_grid_points)
    vandermonde_matrix = np.exp(1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies. Notice the posititve sign inside the exponential
    for iter_num in np.arange(iterations):
        spectrum_without_fftshift = np.fft.fftshift(spectrum,axes=(0,))
        power_vals = np.abs(spectrum_without_fftshift)**2
        double_sided_corr_vect = np.fft.fft(power_vals,num_freq_grid_points)/(num_freq_grid_points)
        single_sided_corr_vec = double_sided_corr_vect[0:signal_length] # r0,r1,..rM-1
        auto_corr_matrix = vtoeplitz(single_sided_corr_vec[None,:])[0,:,:].T
        auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
        Ah_Rinv_y = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv, received_signal),axis=0)
        Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*np.matmul(auto_corr_matrix_inv,vandermonde_matrix),axis=0)
        spectrum = Ah_Rinv_y/Ah_Rinv_A
        print(iter_num)
    return spectrum


def iaa_recursive_levinson_temp(received_signal, digital_freq_grid, iterations):
    '''corr_mat_model_order : must be strictly less than half then signal length'''
    signal_length = len(received_signal)
    num_freq_grid_points = len(digital_freq_grid)    
    spectrum = np.fft.fftshift(np.fft.fft(received_signal.squeeze(),num_freq_grid_points)/(signal_length),axes=(0,))
#    spectrum = np.ones(num_freq_grid_points)
    vandermonde_matrix = np.exp(1j*np.outer(np.arange(signal_length),digital_freq_grid)) # [num_samples,num_freq] # construct the vandermond matrix for several uniformly spaced frequencies. Notice the posititve sign inside the exponential
    for iter_num in np.arange(iterations):
        spectrum_without_fftshift = np.fft.fftshift(spectrum,axes=(0,))
        power_vals = np.abs(spectrum_without_fftshift)**2
        double_sided_corr_vect = np.fft.fft(power_vals,num_freq_grid_points)/(num_freq_grid_points)
        single_sided_corr_vec = double_sided_corr_vect[0:signal_length] # r0,r1,..rM-1
        auto_corr_matrix = vtoeplitz(single_sided_corr_vec[None,:])[0,:,:].T
#        auto_corr_matrix_inv = np.linalg.inv(auto_corr_matrix)
        Rinv_y = solve_levinson_durbin(auto_corr_matrix, received_signal.squeeze())
        Ah_Rinv_y = np.sum(vandermonde_matrix.conj()*Rinv_y[:,None],axis=0)
        Rinv_A = solve_levinson_durbin_ymatrix(auto_corr_matrix, vandermonde_matrix)
        Ah_Rinv_A = np.sum(vandermonde_matrix.conj()*Rinv_A,axis=0)
        spectrum = Ah_Rinv_y/Ah_Rinv_A
        print(iter_num)
    return spectrum









