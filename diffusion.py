import sys, time
import scipy as sp
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
import random as ran
#import pandas as pd


def fig_trimmings(n):
    # add lables
    pad=2.0
    plt.tight_layout(pad=pad, w_pad=pad, h_pad=pad)
    
    plt.subplot(n,1,1)
    plt.xlabel('Distance (km)')
    plt.ylabel('RH')
    plt.axis([0,Ldomain/1000.,0.1,1.1])

    if n>=2:
        plt.subplot(n,1,2)
        plt.xlabel('RH')
        plt.ylabel('PDF')

    if n>=3: 
        plt.subplot(n,1,3)
        plt.xlabel('RH')
        plt.ylabel('Convection occurrence')


def subsidence(crh,opt=1):
    """
    function for subsidence
    """
    if opt==0:
        # subsidence function of humidity to mimic
        # reduction in cooling for very dry columns
        timescale=12.+10*abs(crh-0.6)
    if opt==1:
        # constant except for saturated columns (why?)
        timescale=subsidence_tau
        #if crh>1.0:
        #    timescale=2
    return timescale


def diffusion(T,opt,nrun,subopt=1,noiser=0.0,perc_conv=0.8,Ldomain=2000.,nbar=1.0,nplot=3):
    """
    Simplest expression of the computational algorithm
    for the Backward Euler method, using explicit Python loops
    and a dense matrix format for the coefficient matrix.
    """

    nx=499  # number of points
    
    # diffusion coefficient m*m/s
    # so set K=L*L/S where S is the root of the shear
    # treating deformation radiys as a giant eddy...
    # L=domain length - 10**6
    # treat S**2=du/dz**2 : u=10 m/s z=10**4
    # thus K=10^6 10^6 10^4 / 10
    # need to understand this 
    ustar=1.0
    Lconv=100.e3 # convection scale in m
    diffK=0.4*Ldomain*ustar # diffusion coefficient m^2/s

    # target R from moistening, 3kg/m$^{-2}$ of IWP on 60 kgm2 tcwv:
    crh_detrain=1.05 # check out column ice ratio in detrainment to set this...
    
    # set up grid
    x = np.linspace(0, Ldomain, nx+1)   # mesh points in space
    dx = x[1] - x[0]


    # linestyles
    lslist=['solid','dashed','dotted','dashdot']
    collist=['b','y','r','c','g']
    
    #--- end of setup
    
    F=diffK*dt/(dx*dx)
    
    Nt = int(round(T/float(dt)))
    t = np.linspace(0, T, Nt+1)   # mesh points in time
    crh_0 = np.zeros(nx+1)
    crh_1 = np.zeros(nx+1)

    #diagnostic stuff
    nstore=min(360,Nt)
    crh_store = np.zeros((nstore,nx+1))
    conv_store = np.zeros((nstore))

    bins=np.linspace(0,1,21)
    mbins=(bins[1:]+bins[:-1])/2.0 # midpoints
    nbins=len(bins)-1

    cbins=np.linspace(0.75,1.0,26)
    mcbins=(cbins[1:]+cbins[:-1])/2.0 # midpoints
    ncbins=len(cbins)-1

    # Data structures for the linear system
    A = np.zeros((nx+1, nx+1))
    b = np.zeros(nx+1)
    
    # Set initial condition, constant plus white noise
    crh_0=np.random.normal(loc=crh_init,scale=0.01,size=nx+1)
    
            
    # neighboring points
    ipos= [ i+1 if i<nx else 0 for i in range(0,nx+1) ]
    ineg= [ i-1 if i>0 else nx for i in range(0,nx+1) ]

    #
    for istep in range(0, Nt):
        #print ("step",istep,crh_0.mean())
        
        # define A, implicit
        # with cyclic boundaries
        for i in range(0, nx+1):
            A[i,ineg[i]] = -F
            A[i,ipos[i]] = -F
            subloss=subfac/subsidence(crh_0[i],subopt)
            A[i,i] = 1 + 2*F + subloss # all negative

        # stochastic term goes in here:
        noisedev=noiser*crh_0.std()
        noise=0.0 if noiser<=0.0 else np.random.normal(0.0,noisedev,(nx+1))
        
        # sorted array of water vapor 
        srt=sorted(range(len(crh_0)),key=(crh_0+noise).__getitem__)
        
        # conv location options
        if opt==1:
            # added in noise
            index=(crh_0+noise).argmax()
        if opt==2:
            index=np.random.randint(nx)
            #print ("idx ",index)
        if opt==3:
            # this selects the perc_conv percentile:
            index=srt[int(perc_conv*(nx+1))]

        # record convection as a function of TCWV
        conv_store=np.roll(conv_store,1)
        conv_store[0]=crh_0[index]
        
        # now do RHS
        b=crh_0

        # convection source term - set RHS to 1 and remove implicit terms
        #A[index,:]=0.0
        #A[index,index]=1.0
        #b[index]=crh_det # answer required at max

        A[index,index]+=crh_detrain
        
        # Compute b and solve linear system
        crh_1[:] = np.linalg.solve(A, b)
        
        # Update crh_0 before next step
        crh_0, crh_1 = crh_1, crh_0

        # rotate storage and store the last day
        crh_store=np.roll(crh_store,1,axis=0)
        crh_store[0,:]=crh_0

    # run finished - clip all R values to saturation
    crh_store=np.clip(crh_store,0.0,1.0)
        
    # convective source at position index
    crh_mean=np.mean(crh_store,axis=0)

    plt.subplot(nplot,1,1)
    plt.plot(x/1000.,crh_mean,linestyle=lslist[nrun[0]],
             color=collist[nrun[0]],lw=2)

    # steadily decreasing size
    # linestyles as a function of nrun
    plt.subplot(nplot,1,2)

    pdf,binsnew = np.histogram(crh_mean,bins=bins)
    #pdf=pdf/float(sum(pdf)) # normalize
    pdf=pdf/float(max(pdf)) # normalize

    # option 1: bars centered but with different widths
    #wx=1.0/(nbins*(nrun[0]+1)) # wide
    #offset=0.0
    #plt.bar(mbins+offset,pdf,width=wx,color=collist[nrun[0]],align='center')
    
    # option 2: bars offset of same width
    wx=1.0/(nbins*(nbar+1.0)) # fixed width
    offset=wx/2.0+wx*nrun[0]    
    plt.bar(bins[:-1]+offset,pdf,width=wx,color=collist[nrun[0]])

    # plot three is the convection PDF
    if nplot>=3:
        plt.subplot(nplot,1,3)
        pdf,binsnew = np.histogram(conv_store,bins=cbins)
        #pdf=pdf/float(sum(pdf)) # normalize
        pdf=pdf/float(max(pdf)) # normalize
        plt.plot(mcbins,pdf,linestyle=lslist[nrun[0]],
             color=collist[nrun[0]],lw=2)
    
    # increment nrun
    nrun[0] += 1
    return nrun

#-----------------------------------------------------------------------
if __name__ == '__main__':

    # set up figure

    nday=50
    subopt=1
    Ldomain=2000*1000.
    Lrun=3600*24*nday
    noiselist=[0.0,0.1,0.5]
    legsize=12
    dt = 3600. # inseconds

    # this DT/timescale of subsidence drying...
    tau_sub=dt/(20.*86400.) #
    # this is dt/tau of convective moistening
    tau_cnv=dt/(3600.) # days

    crh_init=0.8
    
    #subfac=dt/86400.

    #
    # random or organised
    #
    print('random-organised')
    
    nrun=[0]
    plt.figure(1)
    print ("meth1")
    diffusion(Lrun,1,nrun,noiser=0.0,Ldomain=Ldomain,subopt=subopt,nplot=3)
    print ("meth2")
    diffusion(Lrun,2,nrun,noiser=0.0,Ldomain=Ldomain,subopt=subopt,nplot=3)
    fig_trimmings(3)
    
    fig,ax=plt.subplots(3,1,1)
    plt.legend(['Organised','Random'],loc=7,frameon=False,prop={'size':legsize})
    plt.savefig('diffusion_random_organised_subopt'+str(subopt)+'.pdf')
    plt.clf()

    # 
    # MAX + noise 
    #
    print('max-noise')
    nrun=[0]
    nplot=2
    plt.figure(1)
    for noise in noiselist:
        diffusion(Lrun,1,nrun,noiser=noise,Ldomain=Ldomain,nbar=len(noiselist),subopt=subopt,nplot=nplot)

    fig_trimmings(nplot)
    
    legendstr=["Noise Ratio="+str(noise) for noise in noiselist ]
    plt.subplot(nplot,1,1)
    plt.legend(legendstr,loc=8,frameon=False,prop={'size':legsize})
    plt.subplot(nplot,1,2)
#    plt.legend(legendstr,loc=9,frameon=False,prop={'size':legsize})
#    plt.subplot(nplot,1,3)
#    plt.legend(legendstr,loc=6,frameon=False,prop={'size':legsize})
    plt.savefig('diffusion_noise_subopt'+str(subopt)+'.pdf')
    plt.clf()

    
    # 
    # 80% percentile + noise
    #
    print('percentile-organised')

    nrun=[0]
    plt.figure(1)
    for noise in noiselist:
        diffusion(Lrun,3,nrun,noiser=noise,Ldomain=Ldomain,nbar=len(noiselist),subopt=subopt,nplot=nplot)

    fig_trimmings(3)

    # legend location
    #'best'         : 0, (only implemented for axes legends)
    #'upper right'  : 1,
    #'upper left'   : 2,
    #'lower left'   : 3,
    #'lower right'  : 4,
    #'right'        : 5,
    #'center left'  : 6,
    #'center right' : 7,
    #'lower center' : 8,
    #'upper center' : 9,
    #'center'       : 10,

    legendstr=["Noise Ratio="+str(noise) for noise in noiselist ]
    plt.subplot(3,1,1)
    plt.legend(legendstr,loc=1,frameon=False,prop={'size':legsize})
    plt.subplot(3,1,2)
    plt.legend(legendstr,loc=9,frameon=False,prop={'size':legsize})
    plt.subplot(3,1,3)
    plt.legend(legendstr,loc=6,frameon=False,prop={'size':legsize})
    plt.savefig('diffusion_percentile_noise_subopt'+str(subopt)+'.pdf')
    plt.clf()

