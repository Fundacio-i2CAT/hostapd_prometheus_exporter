'''
hostapd_exporter.py
Copyright 2019 Fundacio Privada I2CAT, Internet i Innovacio digital a Catalunya.

See LICENSE for more details
'''

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
import prometheus_client as prometheus
import sys
import time
import json
import os
import subprocess as sp

VERSION = 1.2
DEFAULT_PORT = 9551

metrics_ap = {}
metrics_sta = {}
ctrl_dir = "/var/run/"

def get_hostapd_vaps():
	hostapd_vaps =[]
	output = os.listdir(ctrl_dir)
	for ha_iface in output:
		if ("hostapd" in ha_iface):
			hostapd_vaps.append(ha_iface)
	return hostapd_vaps
		
def get_vap_stats(e):
	vap_status = sp.check_output('hostapd_cli -p '+ctrl_dir+e+' status', universal_newlines=True, shell=True).split('\n')
	vap_stats = {}
	#Remove first entry - 'Selected interface ...'
	vap_status.pop(0)

	for st in vap_status:
		entry = st.split('=')
		if (len(entry) > 1):
			vap_stats[entry[0]] = entry[1]
	return vap_stats		

def get_sta_stats(e):
	all_sta = sp.check_output('hostapd_cli -p '+ctrl_dir+e+' all_sta', universal_newlines=True, shell=True).split('\n')
	all_sta_stats = []
	sta_stats = {}
	#Remove first entry - 'Selected interface ...'
	all_sta.pop(0)

	num_stas = 0
	for st in all_sta:
		entry = st.split('=')
		if (len(entry) > 1):
			sta_stats[entry[0]] = entry[1]
		else:
			if (num_stas > 0):
				all_sta_stats.append(sta_stats)
				sta_stats = {}
			sta_stats['mac_sta'] = entry[0]
			num_stas += 1

	if (num_stas > 0):
		all_sta_stats.append(sta_stats)		
	return all_sta_stats, num_stas

class VAPCollector(object):
	def collect(self):
		hostapd_ctr_ifaces = get_hostapd_vaps()
		for e in hostapd_ctr_ifaces:
			vap_stats = get_vap_stats(e)
			if (len(vap_stats) != 0):
				try:
					vap_label = e.split('_',1)[1]
				except:
					vap_label = 'NONE'
				for metric in vap_stats.keys():
					if (metric in metrics_ap):
						if (metrics_ap[metric][1] == 'gauge'):
							g = GaugeMetricFamily('hostapd_ap_'+metrics_ap[metric][0], metrics_ap[metric][2], labels=['id'])
						else:
							g = CounterMetricFamily('hostapd_ap_'+metrics_ap[metric][0], metrics_ap[metric][2], labels=['id'])
						g.add_metric([vap_label], int(vap_stats[metric]))
						yield g


class STACollector(object):
	def collect(self):
		hostapd_ctr_ifaces = get_hostapd_vaps()
		for e in hostapd_ctr_ifaces:
			sta_stats, num_stas = get_sta_stats(e)
			if (num_stas > 0):
				try:
					vap_label = e.split('_',1)[1]
				except:
					vap_label = 'NONE'
				for sta in sta_stats:
					sta_label = str(sta['mac_sta'])
					for metric in sta.keys():
						if (metric in metrics_sta):
							if (metrics_sta[metric][1] == 'gauge'):
								g = GaugeMetricFamily('hostapd_sta_'+metrics_sta[metric][0], metrics_sta[metric][2], labels=['id', 'mac_sta'])
							else:
								g = CounterMetricFamily('hostapd_sta_'+metrics_sta[metric][0],metrics_sta[metric][2], labels=['id', 'mac_sta'])
							if (metric == "tx_rate_info" or metric == "rx_rate_info"):
								#convert the value to bps
								g.add_metric([vap_label, sta_label], int(sta[metric])*1e5)
							else:
								g.add_metric([vap_label, sta_label], int(sta[metric]))
							yield g

def parse_metrics(metrics_config):
	metrics = {}
	for m in metrics_config:
		try:
			mname = m['name_hostapd']
			pname = m['name_prometheus']
			mtype = m['type']
			mhelp = m['help']
			metrics[mname] = [pname, mtype, mhelp]
		except:
			print("\nError: Please provide a correct metric definition including name, type and help", m)
			exit(-1)
		else:
			if (mtype != 'gauge' and mtype != 'counter'):
				print ("\nError: Only gauge and counter are supported", m)
				exit(-1)
	return metrics

def main():
	global metrics_ap
	global metrics_sta
	global ctrl_dir

	metrics_found = 0
	print ("Hostapd exporter - Version " , str(VERSION))

	#Read config file
	try:
		with open('config.json', 'r') as f:
			config = json.load(f)
	except Exception as e:
		print ("Exception while opening the config.json file: ", e)
		exit(-1)
	
	#Read default port
	try:
		port = config['DEFAULT']['PORT']
	except:
		port = DEFAULT_PORT

	#Read default dir
	try:
		ctrl_dir = config['DEFAULT']['CTRL_IF_DIR']
	except:
		pass

	if not os.path.isdir(ctrl_dir):
		print ("Please, provide a valid directory to find hostapd ctrl ifaces")
		exit(-1)

	#Read metrics
	try:
		metrics_ap = parse_metrics(config['METRICS_AP'])
	except:
		print ("No metrics regarding the APs have been provided")
	else:	
		metrics_found = 1

	try:
		metrics_sta = parse_metrics(config['METRICS_STA'])
	except:
		print ("No metrics regarding the STAs have been provided")
	else:	
		metrics_found = 1

	#at least one metric should be present
	if not metrics_found:
		print ("Please, provide at least one metric")
		exit(-1)

	REGISTRY.register(VAPCollector())
	REGISTRY.register(STACollector())	
	prometheus.start_http_server(port)

	print ("Prometheus http server started on port", port)

	while True:
		time.sleep(100)

if __name__ == '__main__':
    main()
