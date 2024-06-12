from __future__ import annotations


class UnitFileDefinition:
    # from:
    # https://www.freedesktop.org/software/systemd/man/systemd.unit.html
    # https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files

    class Unit:
        """The first section found in most unit files is the [Unit] section. This is generally used for defining metadata for the unit and configuring the relationship of the
        unit to other units"""

        NAME = "Unit"

        Description = "Description"
        """This directive can be used to describe the name and basic functionality of the unit. It is returned by various systemd tools, so it is good to set this to something
        short, specific, and informative."""
        Documentation = "Documentation"
        """This directive provides a location for a list of URIs for documentation. These can be either internally available man pages or web accessible URLs. The systemctl
        status command will expose this information, allowing for easy discoverability."""
        Requires = "Requires"
        """This directive lists any units upon which this unit essentially depends. If the current unit is activated, the units listed here must successfully activate as well,
        else this unit will fail. These units are started in parallel with the current unit by default."""
        Wants = "Wants"
        """This directive is similar to Requires=, but less strict. Systemd will attempt to start any units listed here when this unit is activated. If these units are not
        found or fail to start, the current unit will continue to function. This is the recommended way to configure most dependency relationships. Again,
        this implies a parallel activation unless modified by other directives."""
        BindsTo = "BindsTo"
        """This directive is similar to Requires=, but also causes the current unit to stop when the associated unit terminates."""
        Before = "Before"
        """The units listed in this directive will not be started until the current unit is marked as started if they are activated at the same time. This does not imply a
        dependency relationship and must be used in conjunction with one of the above directives if this is desired."""
        PartOf = "PartOf"
        """Configures dependencies similar to Requires=, but limited to stopping and restarting of units.
        When systemd stops or restarts the units listed here, the action is propagated to this unit. Note that this is a one-way dependency — changes to this unit do not affect the listed units.
        When PartOf=b.service is used on a.service, this dependency will show as ConsistsOf=a.service in property listing of b.service. ConsistsOf= dependency cannot be specified directly."""
        After = "After"
        """"The units listed in this directive will be started before starting the current unit. This does not imply a dependency relationship and one must be established
        through the above directives if this is required."""
        Conflicts = "Conflicts"
        """This can be used to list units that cannot be run at the same time as the current unit. Starting a unit with this relationship will cause the other units to be
        stopped."""
        Condition = "Condition"
        """There are a number of directives that start with Condition which allow the administrator to test certain conditions prior to starting the unit. This can be used
        to provide a generic unit file that will only be run when on appropriate systems. If the condition is not met, the unit is gracefully skipped."""
        Assert = "Assert"
        """Similar to the directives that start with Condition, these directives check for different aspects of the running environment to decide whether the unit should
        activate. However, unlike the Condition directives, a negative result causes a failure with this directive."""

    class Install:
        """Unit files may include an [Install] section, which carries installation information for the unit. This section is not interpreted by systemd(1) during runtime; it is
        used by the enable and disable commands of the systemctl(1) tool during installation of a unit."""

        NAME = "Install"

        Alias = "Alias"
        """A space-separated list of additional names this unit shall be installed under. The names listed here must have the same suffix (i.e. type) as the unit filename. This
        option may be specified more than once, in which case all listed names are used"""

        WantedBy = "WantedBy"
        """This option may be used more than once, or a space-separated list of unit names may be given. A symbolic link is created in the .wants/ or .requires/ directory of
        each of the listed units when this unit is installed by systemctl enable. This has the effect of a dependency of type Wants= or Requires= being added from the listed
        unit to the current unit. The primary result is that the current unit will be started when the listed unit is started, see the description of Wants= and Requires= in the
        [Unit] section for details."""
        RequiredBy = "RequiredBy"
        """This option may be used more than once, or a space-separated list of unit names may be given. A symbolic link is created in the .wants/ or .requires/ directory of
        each of the listed units when this unit is installed by systemctl enable. This has the effect of a dependency of type Wants= or Requires= being added from the listed
        unit to the current unit. The primary result is that the current unit will be started when the listed unit is started, see the description of Wants= and Requires= in the
        [Unit] section for details."""
        Also = "Also"
        """Additional units to install/deinstall when this unit is installed/deinstalled. If the user requests installation/deinstallation of a unit with this option configured,
        systemctl enable and systemctl disable will automatically install/uninstall units listed in this option as well. This option may be used more than once,
        or a space-separated list of unit names may be given."""

    class Service:
        """From https://www.freedesktop.org/software/systemd/man/systemd.service.html"""

        NAME = "Service"

        class Type:
            """Unit files may include an [Install] section, which carries installation information for the unit. This section is not interpreted by systemd(1) during runtime; it
            is used by the enable and disable commands of the systemctl(1) tool during installation of a unit."""

            NAME = "Type"

            simple = "simple"
            """If set to simple (the default if ExecStart= is specified but neither Type= nor BusName= are), the service manager will consider the unit started immediately after
            the main service process has been forked off. It is expected that the process configured with ExecStart= is the main process of the service. In this mode,
            if the process offers functionality to other processes on the system, its communication channels should be installed before the service is started up (e.g. sockets
            set up by systemd, via socket activation), as the service manager will immediately proceed starting follow-up units, right after creating the main service process,
            and before executing the service's binary. Note that this means systemctl start command lines for simple services will report success even if the service's binary
            cannot be invoked successfully (for example because the selected User= doesn't exist, or the service binary is missing)."""
            exec = "exec"
            """The exec type is similar to simple, but the service manager will consider the unit started immediately after the main service binary has been executed. The
            service manager will delay starting of follow-up units until that point. (Or in other words: simple proceeds with further jobs right after fork() returns,
            while exec will not proceed before both fork() and execve() in the service process succeeded.) Note that this means systemctl start command lines for exec services
            will report failure when the service's binary cannot be invoked successfully (for example because the selected User= doesn't exist, or the service binary is
            missing)."""
            forking = "forking"
            """If set to forking, it is expected that the process configured with ExecStart= will call fork() as part of its start-up. The parent process is expected to exit
            when start-up is complete and all communication channels are set up. The child continues to run as the main service process, and the service manager will consider
            the unit started when the parent process exits. This is the behavior of traditional UNIX services. If this setting is used, it is recommended to also use the
            PIDFile= option, so that systemd can reliably identify the main process of the service. systemd will proceed with starting follow-up units as soon as the parent
            process exits."""
            oneshot = "oneshot"
            """Behavior of oneshot is similar to simple; however, the service manager will consider the unit up after the main process exits. It will then start follow-up units.
            RemainAfterExit= is particularly useful for this type of service. Type=oneshot is the implied default if neither Type= nor ExecStart= are specified. Note that if
            this option is used without RemainAfterExit= the service will never enter "active" unit state, but directly transition from "activating" to "deactivating" or "dead"
            since no process is configured that shall run continuously. In particular this means that after a service of this type ran (and which has RemainAfterExit= not set)
            it will not show up as started afterwards, but as dead."""
            dbus = "dbus"
            """Behavior of dbus is similar to simple; however, it is expected that the service acquires a name on the D-Bus bus, as configured by BusName=. systemd will proceed
            with starting follow-up units after the D-Bus bus name has been acquired. Service units with this option configured implicitly gain dependencies on the dbus.socket
            unit. This type is the default if BusName= is specified. A service unit of this type is considered to be in the activating state until the specified bus name is
            acquired. It is considered activated while the bus name is taken. Once the bus name is released the service is considered being no longer functional which has the
            effect that the service manager attempts to terminate any remaining processes belonging to the service. Services that drop their bus name as part of their shutdown
            logic thus should be prepared to receive a SIGTERM (or whichever signal is configured in KillSignal=) as result."""
            notify = "notify"
            """Behavior of notify is similar to exec; however, it is expected that the service sends a "READY=1" notification message via sd_notify(3) or an equivalent call when
            it has finished starting up. systemd will proceed with starting follow-up units after this notification message has been sent. If this option is used,
            NotifyAccess= (see below) should be set to open access to the notification socket provided by systemd. If NotifyAccess= is missing or set to none,
            it will be forcibly set to main."""
            notify_reload = "notify-reload "
            """Behavior of notify-reload is identical to notify. However, it extends the logic in one way: the SIGHUP UNIX process signal is sent to the service's main process
            when the service is asked to reload. (The signal to send can be tweaked via ReloadSignal=, see below.). When initiating the reload process the service is then
            expected to reply with a notification message via sd_notify(3) that contains the "RELOADING=1" field in combination with "MONOTONIC_USEC=" set to the current
            monotonic time (i.e. CLOCK_MONOTONIC in clock_gettime(2)) in µs, formatted as decimal string. Once reloading is complete another notification message must be sent,
            containing "READY=1". Using this service type and implementing this reload protocol is an efficient alternative to providing an ExecReload= command for reloading of
            the service's configuration."""
            idle = "idle"
            """Behavior of idle is very similar to simple; however, actual execution of the service program is delayed until all active jobs are dispatched. This may be used to
            avoid interleaving of output of shell services with the status output on the console. Note that this type is useful only to improve console output, it is not useful
            as a general unit ordering tool, and the effect of this service type is subject to a 5s timeout, after which the service program is invoked anyway."""

        RemainAfterExit = "RemainAfterExit"
        """This directive is commonly used with the oneshot type. It indicates that the service should be considered active even after the process exits."""
        PIDFile = "PIDFile"
        """If the service type is marked as “forking”, this directive is used to set the path of the file that should contain the process ID number of the main child that should
        be monitored."""
        BusName = "BusName"
        """This directive should be set to the D-Bus bus name that the service will attempt to acquire when using the “dbus” service type."""
        NotifyAccess = "NotifyAccess"
        """This specifies access to the socket that should be used to listen for notifications when the “notify” service type is selected This can be “none”, “main”,
        or "all. The default, “none”, ignores all status messages. The “main” option will listen to messages from the main process and the “all” option will cause all members of
        the service’s control group to be processed."""

        ExecStart = "ExecStart"
        """This specifies the full path and the arguments of the command to be executed to start the process. This may only be specified once (except for “oneshot” services). If
        the path to the command is preceded by a dash “-” character, non-zero exit statuses will be accepted without marking the unit activation as failed."""
        ExecStartPre = "ExecStartPre"
        """This can be used to provide additional commands that should be executed before the main process is started. This can be used multiple times. Again,
        commands must specify a full path and they can be preceded by “-” to indicate that the failure of the command will be tolerated."""
        ExecStartPost = "ExecStartPost"
        "This has the same exact qualities as ExecStartPre= except that it specifies commands that will be run after the main process is started."
        ExecReload = "ExecReload"
        "This optional directive indicates the command necessary to reload the configuration of the service if available."
        ExecStop = "ExecStop"
        "This indicates the command needed to stop the service. If this is not given, the process will be killed immediately when the service is stopped."
        ExecStopPost = "ExecStopPost"
        "This can be used to specify commands to execute following the stop command."
        RestartSec = "RestartSec"
        "If automatically restarting the service is enabled, this specifies the amount of time to wait before attempting to restart the service."
        Restart = "Restart"
        """This indicates the circumstances under which systemd will attempt to automatically restart the service. This can be set to values like “always”, “on-success”,
        “on-failure”, “on-abnormal”, “on-abort”, or “on-watchdog”. These will trigger a restart according to the way that the service was stopped."""
        TimeoutSec = "TimeoutSec"
        """This configures the amount of time that systemd will wait when stopping or stopping the service before marking it as failed or forcefully killing it. You can set
        separate timeouts with TimeoutStartSec= and TimeoutStopSec= as well."""

        KillSignal = "KillSignal"
