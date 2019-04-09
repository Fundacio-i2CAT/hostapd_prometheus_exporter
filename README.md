### Prometheus exporter for hostapd
	
- Uses hostapd_cli to get statistics from the Access Points (APs)/ Virtual Access Points (VAPs) and the connected clients. 

- Tested with hostapd v2.7

- Expects the following name format for the ctrl_interface used in order to connect to hostapd: hostapd_$ID
    - Where each ID is unique and each hostapd instance only manages one AP/VAP
	- Detects the APs/VAPs automatically if a new ctrl iface is addded

- Uses the following labels:
 	- id=$ID (added to the statistics of the VAP/AP with this ID and the clients)
 	- mac_sta=$MAC_STA (added to the statistics of the clients)

- Expects a config.json file for configuration (an example is provided with the code):
    - DEFAULT: port (default 9551) and directory containing the hostapd ctrl ifaces (default '/var/run')

    - METRICS_AP: metrics related to the status of the AP/VAP. For each metric, it expects a name_hostapd (must be one of the obtained metrics when using the 'status' command in hostapd_cli), a name_prometheus (the one that will be exported to prometheus), a type (gauge or counter) and a help/information string

    - METRICS_STA: metrics related to the stations connected to the AP/VAP. For each metric, it expects a name_hostapd (must be one of the obtained metrics when using the 'all_sta' command in hostapd_cli), a name_prometheus (the one that will be exported to prometheus), a type (gauge or counter) and a help/information string

 - Copyright 2019 Fundacio i2CAT <www.i2cat.net>, Miguel Catalan-Cid 
<miguel.catalan@i2cat.net>. See LICENSE for more details 
