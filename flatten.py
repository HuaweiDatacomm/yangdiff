def compileFilePaths(content):
	lines =  content.splitlines()
	result = handleHeader(lines)
	index = result["index"]
	if result["difftype"] == "normal":
		obj_index = 2
		diff_index = 0
	else:
		obj_index = 3
		diff_index = 1
	changes = []
	additions = []
	deletions = []
	indent = getIndent(lines[index])
	path = [result["filename"] + ":"]
	while index < len(lines) and not lines[index].find('\";') != -1:
		line = lines[index]
		split = line.split()
		if index + 1 == len(lines):
			nextIndent = 0
		else:
			nextIndent = getIndent(lines[index + 1])
		if nextIndent > indent:
			indent = nextIndent
			path.append(split[obj_index])
			path.append('/')
		else:
			suffixFound = False
			if obj_index == len(split):
				path.append(split[obj_index - 1])
			elif split[obj_index] == "from":
				suffixFound = True
				path.append(split[obj_index - 1])
				end = " " + " ".join(split[obj_index:])
				path.append(end)
			else:
				path.append(split[obj_index])
			addDiff("".join(path), split[diff_index], changes, additions, deletions)
			num = len(path) - (indent - nextIndent + 1)
			if suffixFound:
				path = path[:num - 1]
			else:
				path = path[:num]
			indent = nextIndent
		index += 1
	return {"header": result["output"], "changes": changes, "additions": additions, "deletions": deletions}

def getIndent(line):
	return len(line) - len(line.lstrip())

def addDiff(path, identifier, changes, additions, deletions):
	print(path)
	if identifier == "Changed" or identifier == "M":
		changes.append(path)
	if identifier == "Added" or identifier == "A":
		additions.append(path)
	if identifier == "Removed" or identifier == "D":
		deletions.append(path)


def handleHeader(lines):
	output = []
	header_parsed = False
	index = 0
	while index < len(lines):
		line = lines[index]
		if not header_parsed:
			if line.startswith("// old:"):
				hdr = line.split()
				if hdr[2].find("/") == -1:
					filename = hdr[2]
				else:
					filename = hdr[2][hdr[2].find("/") + 1:]
				output.append(line)
			elif line.startswith("// new:"):
				output.append(line)
				header_parsed = True
				index += 1
			index += 1
			continue
		else:
			difftype = "normal"
			if line.startswith("  revision"):
				difftype = "revision"
				index += 2
			break
	return {"index": index, "output": output, "filename": filename, "difftype": difftype}
