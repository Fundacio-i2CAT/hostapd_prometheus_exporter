'''
hostapd_exporter.py 
Copyright 2019 Miguel Catalan-Cid <miguel.catalan@i2cat.net>

See LICENSE for more details 
'''

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
import prometheus_client as prometheus
import sys
import commands
import time
import json
import os

VERSION = 1.0
DEFAULT_PORT = 9551

metrics_ap = {}
metrics_sta = {}
ctrl_dir = "/var/run/"

def get_hostapd_vaps():
	output = commands.getstatusoutput("ls -la "+ctrl_dir+ " | grep hostapd | awk '{ print $9 }'")
	if not output[1]:
		print 'VAPs are still not active'
		return {}
	return output[1].split('\n')
		
def get_vap_stats(e):
	vap_status = commands.getstatusoutput('hostapd_cli -p '+ctrl_dir+e+' status')[1].split('\n')
	vap_stats = {}
	#Remove first entry - 'Selected interface ...'
	vap_status.pop(0)

	for st in vap_status:
		entry = st.split('=')
		if (len(entry) > 1):
			vap_stats[entry[0]] = entry[1]
	return vap_stats		

def get_sta_stats(e):
	all_sta = commands.getstatusoutput('hostapd_cli -p '+ctrl_dir+e+' all_sta')[1].split('\n')
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
						if (metrics_ap[metric][0] == 'gauge'):
							g = GaugeMetricFamily('hostapd_ap_'+metric.split('[',1)[0], metrics_ap[metric][1], labels=['id'])
						else:
							g = CounterMetricFamily('hostapd_ap_'+metric.split('[',1)[0], metrics_ap[metric][1], labels=['id'])
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
							if (metrics_sta[metric][0] == 'gauge'):
								g = GaugeMetricFamily('hostapd_sta_'+metric.split('[',1)[0], metrics_sta[metric][1], labels=['id', 'mac_sta'])
							else:
								g = CounterMetricFamily('hostapd_sta_'+metric.split('[',1)[0], metrics_sta[metric][1], labels=['id', 'mac_sta'])
							g.add_metric([vap_label, sta_label], int(sta[metric]))
							yield g

def parse_metrics(metrics_config):
	metrics = {}
	for m in metrics_config:
		try:
			mname = m["name"]
			mtype = m['type']
			mhelp = m['help']
			metrics[mname] = [mtype, mhelp]
		except:
			print "\nError: Please provide a correct metric definition including name, type and help", m
			exit(-1)
		else:
			if (mtype != 'gauge' and mtype != 'counter'):
				print "\nError: Only gauge and counter are supported", m
				exit(-1)
	return metrics

def main():
	global metrics_ap
	global metrics_sta
	global ctrl_dir

	metrics_found = 0
	print "Hostapd exporter - Version "  + str(VERSION)

	#Read config file
	try:
		with open('config.json', 'r') as f:
			config = json.load(f)
	except Exception as e:
		print "Exception while opening the config.json file: ", e
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
		print "Please, provide a valid directory to find hostapd ctrl ifaces"
		exit(-1)

	#Read metrics
	try:
		metrics_ap = parse_metrics(config['METRICS_AP'])
	except:
		print "No metrics regarding the APs have been provided"
	else:	
		metrics_found = 1

	try:
		metrics_sta = parse_metrics(config['METRICS_STA'])
	except:
		print "No metrics regarding the STAs have been provided"
	else:	
		metrics_found = 1

	#at least one metric should be present
	if not metrics_found:
		print "Please, provide at least one metric"
		exit(-1)

	REGISTRY.register(VAPCollector())
	REGISTRY.register(STACollector())	
	prometheus.start_http_server(port)

	print "Prometheus http server started on port", port

	while True:
		time.sleep(100)

if __name__ == '__main__':
    main()
