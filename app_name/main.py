"""
:mod:`app` -- Rest App
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from app_name.di.rest import RestDI

di = RestDI()

di.init_resources()
app = di.app
