Check_jenkins
====================

Origin
-------

I've used Jenkins as a Continuous Integration for a while.

Surprisingly the company I joined recently used it also as an orchestration tool :

We don't only manage our code with jenkins but also let it deal with job that process data. In that context it was important to monitor
the success or failure of a job, but most importantly make sure they don't take too long (https://wiki.jenkins-ci.org/display/JENKINS/Build-timeout+Plugin was not an option)

Nagios also supports escalation which is a nice feature in term of process and SLA in our environment.



### Usage

Define a command 

    # check Jenkins job - Note : we have ssl ON by default
    define command{
        command_name    check_jenkins_job
        command_line    $USER2$/check_jenkins_job.py -H $HOSTNAME$ -j $ARG1$ -w $ARG2$ -c $ARG3$ -u $ARG4$ -p $ARG5$ -S
    }

Then a service

    define service{
         use                     generic-service
         service_description     check_jenkins Process data
         check_command           check_jenkins_job!Large_data_process!360!540!nagios!readonly!
         host_name               ci-01.acme.tld
    }


I'd recomend put the various scripts in folder defined with `$USER2$` in resource.cfg



