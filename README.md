Check\_Jenkins\_*
================

Origin
-------

I've used Jenkins as a Continuous Integration for a while.

Surprisingly the company I joined recently used it also as an orchestration tool :

We don't only manage our code with jenkins but also let it deal with jobs that process data on other jenkins instances. In that context it was important to monitor
the success or failure of a job, but most importantly make sure they don't take too long ([timeout-plugin](https://wiki.jenkins-ci.org/display/JENKINS/Build-timeout+Plugin) was not an option)

Nagios also supports escalation which is a nice feature in term of process and SLA in our environment.



### Usage

#### Command line

You can test it quickly with :

    ./check_jenkins_job.py  -w 200 -c 300  -H builds.apache.org -S -j Hadoop-Common-trunk 


Please don't hammer builds.apache.org

#### Nagios    

##### Define a command 

    # check Jenkins job 
    # Note : we have ssl ON by default
    define command{
        command_name    check_jenkins_job
        command_line    $USER2$/check_jenkins_job.py -S -H $HOSTNAME$ -j $ARG1$ -w $ARG2$ -c $ARG3$ -u $ARG4$ -p $ARG5$ 
    }

##### Then a service

    define service{
         use                     generic-service
         service_description     check_jenkins Process data
         check_command           check_jenkins_job!Large_data_process!360!540!nagios!readonly!
         host_name               data-process-01.acme.tld
    }


I'd recommend to put the various scripts in a folder defined with `$USER2$` in resource.cfg, to avoid having it with system package based checks in `$USER1$`



