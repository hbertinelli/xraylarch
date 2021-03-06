#!/usr/bin/env python
"""
provide xrf_peak() function to create an  XRF_Peak.
This is a Larch group representing a Peak in an XRF Spectrum.

  group  = xrf_peak()

"""
import six
import numpy as np
from scipy.interpolate import UnivariateSpline
from larch import (Group, Parameter, isParameter,
                   ValidateLarchPlugin,
                   param_value, isNamedClass)

from larch_plugins.xray import xray_line, xray_lines
from larch_plugins.math import gaussian, lorentzian, voigt, pvoigt

class XRFPeak(Group):
    def __init__(self, name=None, shape='gaussian',
                 amplitude=1, center=0, sigma=1,
                 sigma_params=None, _larch=None, **kws):
        self._larch = _larch
        kwargs = {'name': name}
        kwargs.update(kws)
        self.amplitude = amplitude
        self.center   = center
        self.sigma = sigma
        Group.__init__(self)
        self.name = name
        if name is not None:
            self._define(name, shape=shape,
                         sigma_params=sigma_params)

    def _define(self, name, shape='gaussian', sigma_params=None):
        self.shape = shape
        if name is None:
            return
        try:
            elem, line = [w.title() for w in name.split()]
        except:
            return
        if line == 'Ka': line='Ka1'

        dat = xray_line(elem, line, _larch=self._larch)
        if dat is not None:
            ecenter = dat[0]
            if self.center is None:
                self.center = Parameter(name='center',
                                        value=ecenter,
                                        vary=False,
                                        _larch=self._larch)

            if sigma_params is not None:
                if len(sigma_params) == 2 and self.sigma is None:
                    if isParameter(sigma_params[0]):
                        sigma_params = (sigma_params[0].name,
                                        sigma_params[1].name)
                    expr = "%s + %s * %f" % (sigma_params[0],
                                             sigma_params[1],
                                             ecenter)
                    self.sigma = Parameter(name='sigma',
                                           expr=expr,
                                           _larch=self._larch)

    def __repr__(self):
        if self.name is not None:
            return '<XRFPeak Group: %s>' % self.name
        return '<XRFPeak Group (unknown)>'

    def __copy__(self):
        return XRFPeak(name=self.name, _larch=self._larch)

    def __deepcopy__(self, memo):
        return XRFPeak(filename=self.ename, _larch=self._larch)


    def _peakparams(self, paramgroup=None, **kws):
        """evaluate peak parameter values        """
        # sigma, amplitude, center
        if (paramgroup is not None and
            self._larch.symtable.isgroup(paramgroup)):
            self._larch.symtable._sys.paramGroup = paramgroup
        self._larch.symtable._fix_searchGroups()

        out = []
        for parname in ('amplitude', 'sigma', 'center'):
            val = getattr(self, parname)
            if parname in kws:
                if kws[parname] is not None:
                    val = kws[parname]
            if isinstance(val, six.string_types):
                thispar = Parameter(expr=val, _larch=self._larch)
                setattr(self, parname, thispar)
                val = getattr(self, parname)
            out.append(param_value(val))
        return out

    def calc_peak(self, x, amplitude=None, center=None, sigma=None,
                   shape=None, **kws):
        """
        calculate peak function for x values, write to 'counts' attribute
        """
        (amp, sigma, center) = self._peakparams(amplitude=amplitude,
                                                center=center,
                                                sigma=sigma)
        fcn = gaussian
        if shape is None:
            shape = self.shape
        if shape.lower().startswith('loren'):
            fcn = lorentzian
        elif shape.lower().startswith('voig'):
            fcn = voigt
        elif shape.lower().startswith('pvoig'):
            fcn = pvoigt

        self.counts =  amp*fcn(x, cen=center, sigma=sigma)

@ValidateLarchPlugin
def xrf_peak(name=None, amplitude=1, sigma=0.1,
             center=None, shape='gaussian',
             sigma_params=None, _larch=None, **kws):
    """create an XRF Peak

    Parameters:
    -----------
      name:  name of peak -- may be used for auto-setting center
             'Fe Ka1',  'Pb Lb1', etc
      amplitude:
      center:
      sigma:
      shape   peak shape (gaussian, voigt, lorentzian)

    For all the options described as **value or parameter** either a
    numerical value or a Parameter (as created by param()) can be given.

    Returns:
    ---------
        an XRFPeak Group.

    """
    return XRFPeak(name=name, amplitude=amplitude, sigma=sigma, center=center,
                    shape=shape, sigma_params=sigma_params, _larch=_larch)

def registerLarchPlugin():
    return ('_xrf', {'xrf_peak': xrf_peak})
