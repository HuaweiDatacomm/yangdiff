import subprocess
import requests
from django.conf import settings
import django
import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


MY_TOKEN = settings.MY_TOKEN

def fileCompare(oldvers, oldfile, newvers, newfile, difftype):
	#result = getAndOrModifyFiles(oldvers, oldfile, True)
	#if result['errors']:
	#	return {"output": "", "errors": result["errors"], "warnings": []}
	#result = getAndOrModifyFiles(newvers, newfile, False)
	#if result['errors']:
	#	return {"output": "", "errors": result["errors"], "warnings": []}
	# warnings = []
	# result = checkForValidFiles(oldfile[:-5] + "-" + oldvers[:6], "yang_old")
	# print (result)
	# if result['errors']:
		# return {"output": "", "errors": result["errors"], "warnings": result['warnings']}
	# if result['warnings']:
		# warnings += result['warnings']
	# result = checkForValidFiles(newfile[:-5], "yang_new")
	# if result['errors']:
		# return {"output": "", "errors": result["errors"], "warnings": result['warnings']}
	# if result['warnings']:
		# warnings += result['warnings']
	os.chdir("/root/yang/network-router/" + newvers)
	subpr = subprocess.run([
		"yangdiff-pro",
		"--old=/root/yang/network-router/" + oldvers + oldfile,
		"--new=/root/yang/network-router/" + newvers + newfile,
		"--difftype=" + difftype,
		"--header=true"], capture_output=True, text=True)
	# subpr2 = subprocess.run([
		# "pyang", 
		# "-f", 
		# "yin", 
		# "/root/report.yang",  
		# "-o",
		# "/root/report.yang"], capture_output=True, text=True)
	output = subpr.stdout.strip('\n')
	errors = []
	if output.startswith("Error"):
		errors.append("Comparison Unsuccessful")
	return {"output": cleanOutput(output, oldvers, newvers), "errors": errors}

def cleanOutput(output, oldvers, newvers):
	result = []
	i = 0
	lines = output.splitlines()
	# no diff was found
	if len(lines) == 2 or (len(lines) == 7 and lines[3].lstrip().startswith("revision")):
		return "No Difference Found!"
	header_parsed = False
	while i < len(lines):
		line = lines[i]
		if not header_parsed:
			if line.startswith("Warning: Module") and line.endswith("not used"):
				# this warning will be taken care of through pyang
				i += 3
				continue
			if line.startswith("// old:"):
				oldHeader = line.split()
				oldHeader[2] = oldvers + oldHeader[2]
				oldHeader[4] = oldHeader[4]
				line = ' '.join(oldHeader)
			if line.startswith("// new:"):
				newHeader = line.split()
				newHeader[2] = newvers  + newHeader[2]
				newHeader[4] = newHeader[4]
				line = ' '.join(newHeader)
				header_parsed = True
		result.append(line)
		i += 1
	return '\n'.join(result)

def createYangDirectories():
	subprocess.run([
		"mkdir",
		"yang_old"])
	subprocess.run([
		"mkdir",
		"yang_new"])

def emptyYangDirectories():
	subprocess.call("rm -r yang_old/*", shell=True)
	subprocess.call("rm -r yang_new/*", shell=True)

def getAndOrModifyFiles(vers, file, isOld):
	file_list = [file[:-5]]
	completed = set()
	primaryFileChecked = False
	while file_list:
		cur = file_list.pop()
		
		if cur in completed:
			continue
		if isOld:
			f = open("yang_old/" + cur + "-" + vers[:6] + ".yang", "w+")
		else:
			f = open("yang_new/" + cur + ".yang", "w+")
		url = "https://raw.githubusercontent.com/Huawei/yang/d3edbc33ee7e2da65b251aa02b92cbaa625008a7/network-router/" + vers + "/" + cur + ".yang"
		print (url)
		#  proxy = {'https': 'http://r00123726:Aa123456@proxycn2.huawei.com:8080','http': 'http://r00123726:Aa123456@proxycn2.huawei.com:8080'}
		content = requests.get(url, auth=('dmads98', MY_TOKEN),verify=False)
		
		if (content.status_code == 404):
			return {"errors": ["File Not Found: " + vers + "/" + cur + ".yang"]}
		if not primaryFileChecked:
			primaryFileChecked = True
			if content.text.startswith("submodule"):
					return {"errors":  ["Please select a primary module or types file to compare. You have selected a submodule." +
				"\nA node tree cannot be constructed from this file."]}
		header_parsed = False
		filename_parsed = False
		
		for line in content.text.splitlines(True):
			if header_parsed or line.find("/*") != -1:
				f.write(line)
				continue
			if not filename_parsed:
				filename_parsed = True
				if isOld:
					f.write(modifyLine(line, vers)[0])
				else:
					f.write(line)
				continue
			if line.find("import") != -1 or line.find("include") != -1 or line.find("belongs-to") != -1:
				tab = len(line) - len(line.lstrip())
				if isOld:
					result = modifyLine(line[tab:], vers)
					file_list.append(result[1].strip(';'))
					
					f.write(line[:tab] + result[0])
				else:
					file_list.append(line[tab:].split()[1].strip(';'))
					f.write(line)
				continue
			if line.find("organization") >= 0:
				header_parsed = True
			f.write(line)
		f.close()
		completed.add(cur)
	return {"errors": []}

def modifyLine(line, vers):
	words = line.split()
	file_name = words[1].strip(';')
	words[1] = words[1].strip(';') + "-" + vers[:6]
	if len(words) == 2:
		words[1] = words[1] + ";"
	words.append('\n')
	return [' '.join(words), file_name]

def checkForValidFiles(file, dir_name):
	subpr = subprocess.run([
		"pyang", 
		"-f", 
		"tree", 
		dir_name + "/" + file + ".yang",  
		"-p",
		dir_name], capture_output=True, text=True)
	if subpr.stderr != "":
		index = subpr.stderr.find("]")
		if index != -1:
			# this error should not occur. would be caught by getAndOrModifyFiles()
			# occurs when file path given to pyang does not exist
			return {"errors": ["File set invalid", (subpr.stderr[index + 2:]).strip('\n')], "warnings": []}
		errors = []
		warnings = []
		for line in subpr.stderr.splitlines():
			if line.find("error") != -1:
				line = line[line.find("error: ") + 7:]
				line = line[:1].upper() + line[1:]
				errors.append(line)
			else:
				line = line[line.find("warning: ") + 9:]
				line = line[:1].upper() + line[1:]
				warnings.append(line)
		return {"errors": errors, "warnings": warnings}
	return {"errors": [], "warnings": []}

# ========================================================================================================================================
# Uploaded Files Handling

# decent amount of repeated code structurally, could look into refactoring this code up to you to make it 
# cleaner and more readable

def handleUploadedFiles(files, oldPrimary, newPrimary, difftype):
	result = prepareInfo(files, True, oldPrimary)
	warnings = []
	if result["errors"]:
		return {"output": "", "errors": result["errors"], "warnings": warnings}
	if result['warnings']:
		warnings += result['warnings']
	result = prepareInfo(files, False, newPrimary)
	if result["errors"]:
		return {"output": "", "errors": result["errors"], "warnings": warnings}
	if result['warnings']:
		warnings += result['warnings']
	result = checkForValidFiles(oldPrimary[:-5] + "-000", "yang_old")
	if result['errors']:
		return {"output": "", "errors": result["errors"], "warnings": result['warnings']}
	if result['warnings']:
		warnings += result['warnings']
	result = checkForValidFiles(newPrimary[:-5], "yang_new")
	if result['errors']:
		return {"output": "", "errors": result["errors"], "warnings": result['warnings']}
	if result['warnings']:
		warnings += result['warnings']
	subpr = subprocess.run([
		"yangdiff-pro",
		"--old=yang_old/" + oldPrimary[:-5] + "-000" + ".yang",
		"--new=yang_new/" + newPrimary,
		"--modpath=" + "yang_old:yang_new",
		"--difftype=" + difftype,
		"--header=false"], capture_output=True, text=True)
	output = subpr.stdout.strip('\n')
	errors = []
	if output.startswith("Error"):
		errors.append("Comparison Unsuccessful")
	return {"output": cleanUploadOutput(output), "errors": errors, "warnings": warnings}

def cleanUploadOutput(output):
	result = []
	i = 0
	lines = output.splitlines()
	# no diff was found
	if len(lines) == 2 or (len(lines) == 7 and lines[3].lstrip().startswith("revision")):
		return "No Difference Found!"
	header_parsed = False
	while i < len(lines):
		line = lines[i]
		if not header_parsed:
			if line.startswith("Warning: Module") and line.endswith("not used"):
				# this warning will be taken care of through pyang
				i += 3
				continue
			if line.startswith("// old:"):
				oldHeader = line.split()
				oldHeader[2] = oldHeader[2][:-4]
				oldHeader[4] = oldHeader[4][:-9] + ".yang"
				line = ' '.join(oldHeader)
				header_parsed = True
		result.append(line)
		i += 1
	return '\n'.join(result)

def prepareInfo(files, isOld, primaryFile):
	if isOld:
		modules = files.getlist('old_modules')
	else:
		modules = files.getlist('new_modules')
	file_dict = {}
	for file in modules:
		file_dict[file.name] = file
	if isOld:
		return modifyUploadedFiles("000", file_dict, primaryFile, True)
	else:
		return modifyUploadedFiles("111", file_dict, primaryFile, False)

def modifyUploadedFiles(vers, file_map, primary, isOld):
	file_list = [file_map[primary]]
	primaryFileChecked = False
	completed = set()
	while file_list:
		cur = file_list.pop()
		if cur.name in completed:
			continue
		if isOld:
			f = open("yang_old/" + cur.name[:-5] + "-" + vers + ".yang", "wb+")
		else:
			f = open("yang_new/" + cur.name[:-5] + ".yang", "wb+")
		header_parsed = False
		filename_parsed = False
		for line in cur:
			line = line.decode("utf-8")
			if header_parsed or line.find("/***") != -1:
				f.write(line.encode())
				continue
			if not filename_parsed:
				filename_parsed = True
				if not primaryFileChecked:
					primaryFileChecked = True
					if line.startswith("submodule"):
						return {"errors":  ["Please select a primary module or types file to compare. You have selected a submodule." +
							"\nA node tree cannot be constructed from this file."], "warnings": []}
				if isOld:
					f.write(modifyLine(line, vers)[0].encode())
				else:
					f.write(line.encode())
				continue
			if line.find("import") != -1 or line.find("include") != -1 or line.find("belongs-to") != -1:
				tab = len(line) - len(line.lstrip())
				if isOld:
					result = modifyLine(line[tab:], vers)
					# file_list.append(result[1])
					fl = result[1] + ".yang"
					if fl not in file_map.keys():
						return {"errors": ["File Not Found in Old Modules: " + fl]}
					else:
						file_list.append(file_map[fl])
					f.write((line[:tab] + result[0]).encode())
				else:
					fl = line[tab:].split()[1] + ".yang"
					if fl not in file_map.keys():
						return {"errors": ["File Not Found in New Modules: " + fl]}
					else:
						file_list.append(file_map[fl])
					f.write(line.encode())
				continue
			if line.find("organization") >= 0:
				header_parsed = True
			f.write(line.encode())
		f.close()
		completed.add(cur.name)
	if (len(completed) == len(file_map)):
		return {"errors": [], "warnings": []}
	if isOld:
		return {"errors": [], "warnings": ["You have uploaded some unnecessary old modules for the comparison."]}
	else:
		return {"errors": [], "warnings": ["You have uploaded some unnecessary new modules for the comparison."]}


def main():
	# emptyYangDirectories()
	# createYangDirectories()
	result = fileCompare("8.20.10/ne40e-x8x16/", "huawei-aaa.yang", 
		"8.21.0/ne40e-x8x16/", "huawei-aaa.yang", "revision")
	print(result["output"])

if __name__ == "__main__":
	main()

	

