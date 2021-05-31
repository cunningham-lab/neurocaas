Protocols API Reference
=======================

The main functions of the NeuroCAAS Job Manager are contained in the submit_start module: 

.. automodule:: ncap_iac.protocols.submit_start
    :members:

Logging is handled by the log module:

.. automodule:: ncap_iac.protocols.log
    :members:

Finally some examples of postprocessing can be found in the postprocess module:

.. automodule:: ncap_iac.protocols.postprocess
    :members:

We have a bunch of utilities that our Job Managers can access in deployment:

These correspond to specific boto3 modules and are designed to be as isolated as possible. 

.. automodule:: ncap_iac.protocols.utilsparam.s3
    :members:

.. automodule:: ncap_iac.protocols.utilsparam.ec2
    :members:

.. automodule:: ncap_iac.protocols.utilsparam.iam
    :members:

.. automodule:: ncap_iac.protocols.utilsparam.ssm
    :members:

.. automodule:: ncap_iac.protocols.utilsparam.events
    :members:

.. automodule:: ncap_iac.protocols.utilsparam.pricing
    :members:
   
.. automodule:: ncap_iac.protocols.utilsparam.serverless
    :members:
