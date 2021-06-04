import numpy as np;
import torch;
from typing import Tuple;

from Network import Neural_Network;
from Loss_Functions import IC_Loss, Periodic_BC_Loss, Data_Loss, Collocation_Loss;


def Discovery_Training(
        u_NN                : Neural_Network,
        N_NN                : Neural_Network,
        Collocation_Coords  : torch.Tensor,
        Data_Coords         : torch.Tensor,
        Data_Values         : torch.Tensor,
        Optimizer           : torch.optim.Optimizer) -> None:
    """ This function runs one epoch of training when in "Discovery" mode. In
    this mode, we enforce the leaned PDE at the Collocation_Points, and the
    Data_Values at the Data_Points.

    Note: This function works regardless of how many spatial variables u depends
    on so long as Collocation_Loss does too.

    ----------------------------------------------------------------------------
    Arguments:

    u_NN: The network that approximates the PDE solution.

    N_NN: Neural network that approximates the PDE.

    Collocation_Coords: the collocation points at which we enforce the learned
    PDE. If u accepts d spatial coordinates, then this should be a d+1 column
    tensor whose ith row holds the t, x_1,... x_d coordinates of the ith
    Collocation point.

    Data_Coords: A tensor holding the coordinates of the points at which we
    compare the approximate solution to the true one. If u accepts d spatial
    coordinates, then this should be a d+1 column tensor whose ith row holds the
    t, x_1,... x_d coordinates of the ith Data point.

    Data_Values: A tensor holding the value of the true solution at the data
    points. If Data_Coords has N rows, then this should be an N element tensor
    of floats whose ith element holds the value of the true solution at the ith
    data point.

    optimizer: the optimizer we use to train u_NN and N_NN. It should be
    loaded with the gradients of both networks.

    ----------------------------------------------------------------------------
    Returns:

    Nothing! """

    # Zero out the gradients.
    Optimizer.zero_grad();

    # Evaluate the Loss (Note, we enforce a BC of 0)
    Loss = (Collocation_Loss(
                u_NN = u_NN,
                N_NN = N_NN,
                Collocation_Coords = Collocation_Coords)

            +

            Data_Loss(
                u_NN = u_NN,
                Data_Coords = Data_Coords,
                Data_Values = Data_Values));

    # Back-propigate to compute gradients of Loss with respect to network
    # parameters.
    Loss.backward();

    # update network weights.
    Optimizer.step();



def Discovery_Testing(
        u_NN                : Neural_Network,
        N_NN                :  Neural_Network,
        Collocation_Coords  : torch.Tensor,
        Data_Coords         : torch.Tensor,
        Data_Values         : torch.Tensor) -> Tuple[float, float]:
    """ This function runs testing when in "Discovery" mode. You CAN NOT run this
    function with no_grad set True. Why? Because we need to evaluate derivatives
    of the solution with respect to the inputs! Thus, we need torch to build a
    computational graph.

    Note: This function works regardless of how many spatial variables u depends
    on so long as Collocation_Loss does too.

    ----------------------------------------------------------------------------
    Arguments:

    u_NN: The network that approximates the PDE solution.

    N_NN: Neural network that approximates the learned PDE.

    Collocation_Coords: the collocation points at which we enforce the learned
    PDE. If u accepts d spatial coordinates, then this should be a d+1 column
    tensor whose ith row holds the t, x_1,... x_d coordinates of the ith
    Collocation point.

    Data_Coords: A tensor holding the coordinates of the points at which we
    compare the approximate solution to the true one. If u accepts d spatial
    coordinates, then this should be a d+1 column tensor whose ith row holds the
    t, x_1,... x_d coordinates of the ith Data point.

    Data_Values: A tensor holding the value of the true solution at the data
    points. If Data_Coords has N rows, then this should be an N element tensor
    of floats whose ith element holds the value of the true solution at the ith
    data point.

    ----------------------------------------------------------------------------
    Returns:

    a tuple of floats. The first element holds the collocation loss, while
    the second holds the data loss. """

    # Get the losses at the passed collocation points (Note we enforce a 0 BC)
    Coloc_Loss : float = Collocation_Loss(
                            u_NN = u_NN,
                            N_NN = N_NN,
                            Collocation_Coords = Collocation_Coords).item();
    Data_loss : float  = Data_Loss(
                            u_NN = u_NN,
                            Data_Coords = Data_Coords,
                            Data_Values = Data_Values).item();

    # Return the losses.
    return (Coloc_Loss, Data_loss);



def PINNs_Training(
        u_NN                        : Neural_Network,
        N_NN                        : Neural_Network,
        IC_Coords                   : torch.Tensor,
        IC_Data                     : torch.Tensor,
        Lower_Bound_Coords          : torch.Tensor,
        Upper_Bound_Coords          : torch.Tensor,
        Periodic_BCs_Highest_Order  : int,
        Collocation_Coords          : torch.Tensor,
        Optimizer                   : torch.optim.Optimizer) -> None:
    """ This function runs one epoch of training when in "PINNs" mode. In
    this mode, we enforce the leaned PDE at the Collocation_Points, impose
    Initial Conditions (ICs), and Periodic Boundary Condtions (BCs).

    Note: This function works regardless of how many spatial variables u depends
    on so long as Collocation_Loss and Periodic_BC_Loss do too.

    ----------------------------------------------------------------------------
    Arguments:

    u_NN: Neural network that approximates the solution to the learned PDE.

    N_NN: Neural network that approximates the PDE.

    IC_Coords: A tensor that holds the coordinates of each point that we
    enforce the Initial Condition. If u accepts d spatial coordinates, then this
    should be a d+1 column tensor whose ith row holds the t, x_1,... x_d
    coordinates of the ith point where we'll enforce the IC.

    IC_Data: A tensor that holds the value of the initial condition at each
    point in IC_Coords. If IC_Coords has N rows, then this should be an N
    element tensor whose ith entry holds the value of the IC at the ith IC
    point.

    Lower_Bound_Coords: A tensor that holds the coordinates of each grid
    point on the lower spatial bound of the domain.

    Uppder_Bound_Coords: A tensor that holds the coordinates of each grid
    point on the lower spatial bound of the domain.

    Periodic_BCs_Highest_Order: If this is set to N, then we will enforce
    periodic BCs on the solution and its first N-1 derivatives.

    Collocation_Coords: the collocation points at which we enforce the learned
    PDE. If u accepts d spatial coordinates, then this should be a d+1 column
    tensor whose ith row holds the t, x_1,... x_d coordinates the ith
    Collocation point.

    Optimizer: the optimizer we use to train u_NN.

    ----------------------------------------------------------------------------
    Returns:

    Nothing! """

    # Zero out the gradients.
    Optimizer.zero_grad();

    # Evaluate the Loss (Note, we enforce a BC of 0)
    Loss = (IC_Loss(
                u_NN = u_NN,
                IC_Coords = IC_Coords,
                IC_Data = IC_Data)

            +

            Periodic_BC_Loss(
                u_NN = u_NN,
                Lower_Bound_Coords = Lower_Bound_Coords,
                Upper_Bound_Coords = Upper_Bound_Coords,
                Highest_Order = Periodic_BCs_Highest_Order)

            +

            Collocation_Loss(
                u_NN = u_NN,
                N_NN = N_NN,
                Collocation_Coords = Collocation_Coords));

    # Back-propigate to compute gradients of Loss with respect to network
    # parameters
    Loss.backward();

    # update network weights.
    Optimizer.step();



def PINNs_Testing(
        u_NN                        : Neural_Network,
        N_NN                        : Neural_Network,
        IC_Coords                   : torch.Tensor,
        IC_Data                     : torch.Tensor,
        Lower_Bound_Coords          : torch.Tensor,
        Upper_Bound_Coords          : torch.Tensor,
        Periodic_BCs_Highest_Order  : int,
        Collocation_Coords          : torch.Tensor) -> Tuple[float, float, float]:
    """ This function runs one epoch of testing when in "PINNs" mode. In
    this mode, we enforce the leaned PDE at the Collocation_Points, impose
    Initial Conditions (ICs), and Periodic Boundary Condtions (BCs).

    Note: This function works regardless of how many spatial variables u depends
    on so long as Collocation_Loss and Periodic_BC_Loss do too.

    ----------------------------------------------------------------------------
    Arguments:

    u_NN: Neural network that approximates the solution to the learned PDE.

    N_NN: Neural network that approximates the PDE.

    IC_Coords: A tensor that holds the coordinates of each point that we
    enforce the Initial Condition. If u accepts d spatial coordinates, then this
    should be a d+1 column tensor whose ith row holds the t, x_1,... x_d
    coordinates of the ith point where we'll enforce the IC.

    IC_Data: A tensor that holds the value of the initial condition at each
    point in IC_Coords. If IC_Coords has N rows, then this should be an N
    element tensor whose ith entry holds the value of the IC at the ith IC
    point.

    Lower_Bound_Coords: A tensor that holds the coordinates of each grid point
    on the lower spatial bound of the domain.

    Uppder_Bound_Coords: A tensor that holds the coordinates of each grid point
    on the lower spatial bound of the domain.

    Periodic_BCs_Highest_Order: If this is set to N, then we will enforce
    periodic BCs on the solution and its first N-1 derivatives.

    Collocation_Coords: the collocation points at which we enforce the learned
    PDE. If u accepts d spatial coordinates, then this should be a d+1 column
    tensor whose ith row holds the t, x_1,... x_d coordinates the ith
    Collocation point.

    ----------------------------------------------------------------------------
    Returns:

    A tuple of three floats. The 0 element holds the Iniitial Condition loss,
    the 1 element holds the Boundary Condition loss, the 2 element holds the
    Collocation loss. """

    # Get the losses at the passed collocation points (Note we enforce a 0 BC)
    IC_Loss_Var : float     = IC_Loss(
                                u_NN = u_NN,
                                IC_Coords = IC_Coords,
                                IC_Data = IC_Data);

    BC_Loss_Var : float     = Periodic_BC_Loss(
                                u_NN = u_NN,
                                Lower_Bound_Coords = Lower_Bound_Coords,
                                Upper_Bound_Coords = Upper_Bound_Coords,
                                Highest_Order = Periodic_BCs_Highest_Order).item();

    Col_Loss_Var : float    = Collocation_Loss(
                                u_NN = u_NN,
                                N_NN = N_NN,
                                Collocation_Coords = Collocation_Coords).item();

    # Return the losses.
    return (IC_Loss_Var, BC_Loss_Var, Col_Loss_Var);
