"""
Define the TRNFlow airflow network (COMIS) of the building: external nodes with wind pressure coefficients, the wind velocity profile
and the air links between them (cracks and large openings, e.g. windows, doors, a stairwell).
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Connect Network to the input TrnflowNetwork of the Lizard_System component (add that input to the component if it is missing:
TRNFlow is only switched on if the input exists and the list is not empty).  The thermal airnodes of the network are the Lizard
airnodes (their names), the reference height of an airnode is its lowest Z (Lizard_Thermal_Airnode with Trnflow).

Args:
    ----------- External nodes (wind pressure on the façades)
    ExternalNodes (str): names of the external nodes, one per façade at least; the prefix EN_ is added if it is missing
        Access: list
        Required: False
    CpValues (str): wind pressure coefficients of each external node, one text per node with one value per wind direction,
        e.g. "0.8 -0.2 -0.2 -0.2"; a single text is used for all nodes
        Access: list
        Required: False
    WindDirections (str): wind directions of the Cp values in degrees (0 = wind from north, 90 = from east), default "0 90 180 270"
        Access: item
        Required: False
    CpRefHeight (float): height in m above the building reference level (ground) of the wind speed that belongs to the Cp values,
        usually the height of the eaves, default 10
        Access: item
        Required: False
    WindExponent (float): exponent of the wind velocity profile at the building site, 0.15 to 0.25 open terrain, 0.25 to 0.35
        suburb, 0.35 to 0.45 city centre, default 0.25
        Access: item
        Required: False
    ----------- Air links
    LinkNames (str): unique names of the links; the prefix CR_ (crack) or WI_ (opening) is added if it is missing
        Access: list
        Required: False
    LinkTypes (str): CRACK or OPENING per link, default CRACK
        Access: list
        Required: False
    FromNodes (str): name of the node on the From side (external node or airnode), positive flow direction From -> To
        Access: list
        Required: False
    ToNodes (str): name of the node on the To side
        Access: list
        Required: False
    FromHeights (float): height of the link on the From side in m; measured from the building reference level for an external
        node and from the reference height of the node for an airnode, default 0
        Access: list
        Required: False
    ToHeights (float): height of the link on the To side in m (same rule), default 0.  Different absolute heights make the link
        a vertical shaft (not possible for openings with an own height factor of 1)
        Access: list
        Required: False
    Factors (object): factor of each link: opening factor 0 (closed) to 1 (open) of an OPENING or factor of the mass flow
        coefficient of a CRACK (0 closes it); a number or the name of an input such as "INPUT 1*OPEN_WIN" (schedule or control
        in the deck).  Default 1 for a CRACK and 0 for an OPENING
        Access: list
        Required: False
    CrackCs (float): air mass flow coefficient of a CRACK in kg/s at 1 Pa, default 0.002
        Access: list
        Required: False
    CrackExpn (float): flow exponent of a CRACK, 0.5 turbulent to 1 laminar, default 0.66
        Access: list
        Required: False
    OpeningWidth (float): width of the fully open OPENING in m, default 1
        Access: list
        Required: False
    OpeningHeight (float): height of the fully open OPENING in m, default 1
        Access: list
        Required: False
    OpeningCd (float): discharge coefficient of the OPENING, default 0.6
        Access: list
        Required: False
    OpeningOwnHeightFactor (float): 1 = opening in a vertical wall (window, door), 0 = in a horizontal floor or ceiling (one way
        flow only), default 1
        Access: list
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Network (object): connect to the TrnflowNetwork input of the Lizard_System component
        Access: list
"""
version = '1.0.0'
ghenv.Component.Name = "Lizard_Trnflow_Network"
ghenv.Component.NickName = 'Trnflow Network'
ghenv.Component.Message = 'VER %s' % version
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "0 | Project"
import scriptcontext as sc
import Grasshopper.Kernel as gh

DEFAULT_WIND_DIRECTIONS = '0 90 180 270'
DEFAULT_CP_REF_HEIGHT = 10
DEFAULT_WIND_EXPONENT = 0.25
DEFAULT_CRACK_CS = 0.002
DEFAULT_CRACK_EXPN = 0.66
DEFAULT_OPENING_CD = 0.6
OPENING_TYPE = 1                      # LOTYPE and LO1TYPE of the manual's example (casement window / door)
OPENING_SUBTYPE = 4


def inputOf(name):
    """Value of the input called name, None if the component has no such input."""
    return globals().get(name)


def asList(value):
    """Input as a list: None -> [], a single value -> [value]."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def listOf(name):
    return asList(inputOf(name))


def pick(values, index, default):
    """Item index of a list input; the last item is used for the following links (Grasshopper data matching); default if empty."""
    if len(values) == 0:
        return default
    item = values[min(index, len(values) - 1)]
    return default if item is None else item


def single(name, default):
    value = inputOf(name)
    return default if value is None else value


def prefixed(name, prefix):
    name = str(name).strip().replace(' ', '_')
    return name if name.upper().startswith(prefix) else prefix + name


def lookupClass(name):
    """Class of the TRNFlow data objects that Lizard_Component registers (run the project component first)."""
    registered = sc.sticky.get(sc.doc.Path, {})
    if name not in registered:
        raise Exception('%s is not available: run the Lizard project component (Lizard_Component) once first.' % name)
    return registered[name]


def buildNetwork():
    log = []
    network = []
    directions = str(single('WindDirections', DEFAULT_WIND_DIRECTIONS))
    refheight = single('CpRefHeight', DEFAULT_CP_REF_HEIGHT)
    exponent = single('WindExponent', DEFAULT_WIND_EXPONENT)
    nodenames = [prefixed(item, 'EN_') for item in listOf('ExternalNodes')]
    cpvalues = [str(item) for item in listOf('CpValues')]
    if len(nodenames) > 0:
        EXTERNALNODES = lookupClass('EXTERNALNODES')
        WINDVELOCITYPROFILE = lookupClass('WINDVELOCITYPROFILE')
        for index, nodename in enumerate(nodenames):
            cp = pick(cpvalues, index, '')
            if len(cp.split()) != len(directions.split()):
                raise Exception('External node %s: %d Cp values for %d wind directions (%s).' % (
                    nodename, len(cp.split()), len(directions.split()), directions))
            node = EXTERNALNODES()
            node.Name = nodename
            node.Data = 'ENODE %s : CONCENTRATION= 1 : CP= %s\n' % (nodename, cp)
            node.Refheight = refheight
            node.Winddir = directions
            network.append(node)
        # one profile exponent for each wind direction
        for direction in directions.split():
            profile = WINDVELOCITYPROFILE()
            profile.Winddir = direction
            profile.Veloexp = str(exponent)
            network.append(profile)
        log.append('%d external nodes, wind directions %s, Cp reference height %s m, profile exponent %s' % (
            len(nodenames), directions, refheight, exponent))
    linknames = listOf('LinkNames')
    if len(linknames) > 0:
        CRACKS = lookupClass('CRACKS')
        LARGEOPENINGS = lookupClass('LARGEOPENINGS')
    used = set()
    for index in range(len(linknames)):
        kind = str(pick(listOf('LinkTypes'), index, 'CRACK')).strip().upper()
        if kind not in ('CRACK', 'OPENING'):
            raise Exception('Link %s: LinkTypes must be CRACK or OPENING, not %s.' % (linknames[index], kind))
        name = prefixed(linknames[index], 'CR_' if kind == 'CRACK' else 'WI_')
        if name in used:
            raise Exception('Link name %s is used twice.' % name)
        used.add(name)
        ends = []
        for inputname in ('FromNodes', 'ToNodes'):
            end = pick(listOf(inputname), index, None)
            if end is None:
                raise Exception('Link %s needs a From and a To node.' % name)
            # a name of an external node may be given without the EN_ prefix; airnodes keep their name
            end = str(end).strip()
            ends.append(prefixed(end, 'EN_') if prefixed(end, 'EN_') in nodenames else end)
        frheight = pick(listOf('FromHeights'), index, 0)
        toheight = pick(listOf('ToHeights'), index, 0)
        factor = pick(listOf('Factors'), index, 1 if kind == 'CRACK' else 0)
        if kind == 'CRACK':
            link = CRACKS()
            link.Cs = pick(listOf('CrackCs'), index, DEFAULT_CRACK_CS)
            link.Expn = pick(listOf('CrackExpn'), index, DEFAULT_CRACK_EXPN)
        else:
            link = LARGEOPENINGS()
            link.Lotype = OPENING_TYPE
            link.Lo1type = OPENING_SUBTYPE
            link.Lowidth = pick(listOf('OpeningWidth'), index, 1)
            link.Loheight = pick(listOf('OpeningHeight'), index, 1)
            link.Cdopen = link.Cdclose = pick(listOf('OpeningCd'), index, DEFAULT_OPENING_CD)
            link.Wiownhf = pick(listOf('OpeningOwnHeightFactor'), index, 1)
        link.Name = name
        link.Frnode, link.Tonode = ends
        link.Frheight = frheight
        link.Toheight = toheight
        link.Fscale = factor
        network.append(link)
        log.append('%s %s: %s (%s m) -> %s (%s m), factor %s' % (kind, name, link.Frnode, frheight, link.Tonode, toheight, factor))
    return network, '\n'.join(log)


try:
    Network, out = buildNetwork()
except Exception as error:
    Network = []
    out = 'ERROR: %s' % error
    ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Error, str(error))
