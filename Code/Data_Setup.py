import numpy as np;
import torch;
import random;
import scipy.io;

from Settings_Reader import Settings_Container;



class Data_Container:
    pass;



def Data_Loader(Settings : Settings_Container):
    """ This function loads data from file and returns it. We make a few
    assumptions about the data's format. For one, we assume that the .mat file
    contains three fields: t, x, and usol. t and x are ordered lists of the x
    and t grid lines (lines along which there are gridpoints), respectively. We
    assume that the values in x are uniformly spaced. u sol contains the value
    of the true solution at each gridpoint. Each row of usol contains the
    solution for a particular position, while each column contains the solution
    for a particular time.

    If we are in PINNs mode, then we assume the problem has periodic boundary
    conditions (in space). We assume that row 0 of usol contains the value of
    the solution at the periodic boundary. The last row of usol contains the
    solution just before the periodic boundary. This means that x[0] holds the
    x coordinate of the lower bound of the domain, while the last element of x
    holds the x coordinate just before the upper bound of the domain.

    Note: This function is currently hardcoded to work with data involving 1
    spatial dimension.

    ----------------------------------------------------------------------------
    Arguments:

    Settings: What is returned by the Settings_Reader.

    ----------------------------------------------------------------------------
    Returns:

    A Data Container object. What's in that container depends on the mode. """

    # Load data file.
    Data_File_Path = "../Data/" + Settings.Data_File_Name;
    data_in = scipy.io.loadmat(Data_File_Path);

    # Fetch spatial, temporal coordinates and the true solution. We cast these
    # to singles (32 bit fp) since that's what the rest of the code uses.
    t_points    = data_in[Settings.Time_Series_Label] .flatten()[:].astype(dtype = Settings.Numpy_dtype);
    x_points    = data_in[Settings.Space_Series_Label].flatten()[:].astype(dtype = Settings.Numpy_dtype);
    True_Sol_In = (np.real(data_in[Settings.Solution_Series_Label])).astype(dtype = Settings.Numpy_dtype);

    # Add noise to true solution.
    True_Sol_In += (Settings.Noise_Proportion)*np.std(True_Sol_In)*np.random.randn(*True_Sol_In.shape);

    # Generate the grid of (t, x) coordinates where we'll enforce the "true
    # solution". Each row of these arrays corresponds to a particular position.
    # Each column corresponds to a particular time.
    grid_t_coords, grid_x_coords = np.meshgrid(t_points, x_points);

    # Flatten t_coods, x_coords into column vectors.
    flattened_grid_t_coords  = grid_t_coords.reshape(-1, 1);
    flattened_grid_x_coords  = grid_x_coords.reshape(-1, 1);

    # Generate data coordinates, corresponding Data Values.
    All_Data_Coords = np.hstack((flattened_grid_t_coords, flattened_grid_x_coords));
    All_Data_Values = True_Sol_In.flatten();

    # Determine the upper and lower spatial/temporal bounds. t is easy, x is
    # not. x_points only includes the lower spatial bound of the domain. The
    # last element of x_points holds the x value just before the upper bound.
    # Thus, the lower spatial bound is just x_points[0]. The upper spatial bound
    # is x_points[-1] plus the grid spacing (we assume the x values are
    # uniformly spaced).
    x_lower = x_points[ 0];
    x_upper = x_points[-1] + (x_points[-1] - x_points[-2]);
    t_lower = t_points[ 0];
    t_upper = t_points[-1];

    # Initialize data container object. We'll fill this container with different
    # items depending on what mode we're in. For now, fill the container with
    # everything that's ready to ship.
    Container = Data_Container();
    Container.t_points         = t_points;
    Container.x_points         = x_points;
    Container.True_Sol         = True_Sol_In;
    Container.Dim_Lower_Bounds = np.array((t_lower, x_lower), dtype = Settings.Numpy_dtype);
    Container.Dim_Upper_Bounds = np.array((t_upper, x_upper), dtype = Settings.Numpy_dtype);


    if  (Settings.Mode == "PINNs"):
        # If we're in PINN's mode, then we need IC, BC data.

        ############################################################################
        # Initial Conditions
        # Since each column of True_Sol_In corresponds to a particular time, the
        # initial condition is just the 0 column of True_Sol_In. We also need
        # the corresponding coordinates.

        # Get number of spatial, temporal coordinates.
        n_x = len(x_points);
        n_t = len(t_points);

        # There is an IC coordinate for each possible x value. The corresponding
        # time value for that coordinate is 0.
        IC_Coords = np.zeros((n_x, 2), dtype = Settings.Numpy_dtype);
        IC_Coords[:, 1] = x_points;

        # Since each column of True_Sol_In corresponds to a particular time, the
        # 0 column of True_Sol_In holds the initial condition.
        IC_Data = True_Sol_In[:, 0];



        ############################################################################
        # Periodic BC
        # To enforce periodic BCs, at each time, we need the solution to match
        # at the upper and lower spatial bounds.

        # Set up the upper and lower bound coordinates. Let's consider
        # Lower_Bound_Coords. Every coordinate in this array will have the same
        # x coordinate, x_lower. Thus, we initialize an array full of x_lower.
        # We then set the 0 column of this array (the t coordinates) to the
        # set of possible t coordinates (t_points). We do something similar for
        # Upper_Bound_Coords.
        Lower_Bound_Coords = np.full((n_t, 2), x_lower, dtype = Settings.Numpy_dtype);
        Upper_Bound_Coords = np.full((n_t, 2), x_upper, dtype = Settings.Numpy_dtype);
        Lower_Bound_Coords[:, 0] = t_points;
        Upper_Bound_Coords[:, 0] = t_points;

        # Add the tensor version of these items to the container
        Container.IC_Coords        = torch.from_numpy(IC_Coords).to(dtype = Settings.Torch_dtype, device = Settings.Device);
        Container.IC_Data          = torch.from_numpy(IC_Data)  .to(dtype = Settings.Torch_dtype, device = Settings.Device);

        Container.Lower_Bound_Coords = torch.from_numpy(Lower_Bound_Coords).to(dtype = Settings.Torch_dtype, device = Settings.Device);
        Container.Upper_Bound_Coords = torch.from_numpy(Upper_Bound_Coords).to(dtype = Settings.Torch_dtype, device = Settings.Device);

    elif(Settings.Mode == "Discovery"):
        # If we're in Discovery mode, then we need Testing/Training Data
        # coordinates and values.

        # Randomly select Num_Training_Points, Num_Testing_Points coordinate indicies.
        Train_Indicies = np.random.choice(All_Data_Coords.shape[0], Settings.Num_Train_Data_Points, replace = False);
        Test_Indicies  = np.random.choice(All_Data_Coords.shape[0], Settings.Num_Test_Data_Points , replace = False);

        # Now select the corresponding testing, training data points, values.
        # Add everything to the Container.
        Container.Train_Data_Coords = torch.from_numpy(All_Data_Coords[Train_Indicies, :]).to(dtype = Settings.Torch_dtype, device = Settings.Device);
        Container.Train_Data_Values = torch.from_numpy(All_Data_Values[Train_Indicies]).to(dtype = Settings.Torch_dtype, device = Settings.Device);

        Container.Test_Data_Coords  = torch.from_numpy(All_Data_Coords[Test_Indicies, :]).to(dtype = Settings.Torch_dtype, device = Settings.Device);
        Container.Test_Data_Values  = torch.from_numpy(All_Data_Values[Test_Indicies]).to(dtype = Settings.Torch_dtype, device = Settings.Device);

    # The container is now full. Return it!
    return Container;



def Generate_Random_Coords(
        Dim_Lower_Bounds    : np.array,
        Dim_Upper_Bounds    : np.array,
        Num_Points          : int,
        Data_Type           : torch.dtype = torch.float32,
        Device              : torch.device = torch.device('cpu')) -> torch.Tensor:
    """ This function generates a collection of random points within the box
    specified by Dim_Lower_Bounds and Dim_Upper_Bounds.

    ----------------------------------------------------------------------------
    Arguments:

    dim_lower_bounds: If we want to generate points in R^d, then this should be
    a d element array whose kth element stores the lower bound for the kth
    variable.

    dim_upper_bounds: same as dim_lower_bounds but for upper bounds.

    num_Points: The number of points we want to generate.

    Data_Type: The data type used for the coords. Should be torch.float64
    (double precision) or torch.float32 (single precision).

    ----------------------------------------------------------------------------
    Returns:

    A num_Points by d array (where d is the dimension of the space in which the
    points live) whose ith row contains the coordinates of the ith point. """

    # Declare coords array
    d = Dim_Lower_Bounds.size;
    Coords = torch.empty((Num_Points, d), dtype = Data_Type, device = Device);

    # Populate the coordinates with random values.
    for i in range(Num_Points):
        for k in range(d):
            Coords[i, k] = random.uniform(Dim_Lower_Bounds[k], Dim_Upper_Bounds[k]);

    return Coords;
