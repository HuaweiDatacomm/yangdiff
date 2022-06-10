from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
import requests
import json
from django.conf import settings
import subprocess
from .yangdiff import fileCompare, emptyYangDirectories, handleUploadedFiles
from .flatten import compileFilePaths

# Create your views here.

# using my own github personal access token to allow for up to 5000 authenticated requests per hour
# needs to be changed, will change with addition of database
# storing token in .bashrc
MY_TOKEN = settings.MY_TOKEN


def compare_page(request):
	context = {"title": "Yang Compare"}
	template_name = "yang_compare/compare.html"
	#template_obj = get_template(template_name)
	#rendered_item = template_obj.render(context)
	return render(request, template_name, context)

def getDropDownVersions(request):
	if request.method == "GET" and request.is_ajax():
		results = []
		vers_req = requests.get('https://raw.githubusercontent.com/Huawei/yang/d3edbc33ee7e2da65b251aa02b92cbaa625008a7/network-router/', auth=('dmads98', MY_TOKEN))
		json = vers_req.json()
		for el in json:
			if (el["type"] == "dir"):
				results.append({
					"name": el["name"],
					"value": el["name"],
					"text": el["name"]
					})
		return JsonResponse({"success": True, "results": results}, status=200)
	return JsonResponse({"success": False}, status=400)

def getDropDownFiles(request, vers):
	if request.method == "GET" and request.is_ajax():
		results = []
		file_req = requests.get('https://raw.githubusercontent.com/Huawei/yang/d3edbc33ee7e2da65b251aa02b92cbaa625008a7/network-router/' + vers, auth=('dmads98', MY_TOKEN))
		json = file_req.json()
		for el in json:
			if (el["name"].endswith(".yang")):
				results.append({
					"name": el["name"][:-5],
					"value": el["name"],
					"text": el["name"][:-5]
					})
		return JsonResponse({"success": True, "results": results}, status=200)
	return JsonResponse({"success": False}, status=400)

def getFileContent(request, vers, file):
	if request.method == "GET" and request.is_ajax():
		url = "https://raw.githubusercontent.com/Huawei/yang/d3edbc33ee7e2da65b251aa02b92cbaa625008a7/network-router/" + vers + "/" + file
		content_req = requests.get(url, auth=('dmads98', MY_TOKEN))
		if content_req.text.startswith("404"):
			return JsonResponse({"success": False, "version": vers, "file": file}, status=400)
		return JsonResponse({"success": True, "content": content_req.text}, status=200)
	return JsonResponse({"success": False}, status=400)

def compareFiles(request, oldvers, oldfile, newvers, newfile, difftype):
	if request.method == "GET" and request.is_ajax():
		result = fileCompare(oldvers, oldfile, newvers, newfile, difftype)
		emptyYangDirectories()
		return JsonResponse({"success": True, "diff": result["output"], "errors": result["errors"], "warnings": result["warnings"]}, status=200)
	return JsonResponse({"success": False}, status=400)

def fileUpload(request, oldPrimary, newPrimary, difftype):
	if request.method == "POST" and request.is_ajax():
		result = handleUploadedFiles(request.FILES, oldPrimary, newPrimary, difftype)
		emptyYangDirectories()
		return JsonResponse({"success": True, "diff": result["output"], "errors": result["errors"], "warnings": result["warnings"]}, status=200)
	return JsonResponse({"success": False}, status=400)

def constructFilePaths(request):
	if request.method == "POST" and request.is_ajax():
		result = compileFilePaths(request.POST['content'])
		return JsonResponse({"success": True, "header": result["header"], "changes": result["changes"], 
			"additions": result["additions"], "deletions": result["deletions"]}, status=200)
	return JsonResponse({"success": False}, status=400)
