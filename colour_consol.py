import csv, glob,os,re,subprocess

def conv_rgb(colour : int) -> tuple[int,int,int]:
    red = int(colour) & 0xff
    green = (int(colour) >> 8) & 0xff
    blue = (int(colour) >> 16) & 0xff
    return red,green,blue

to_compress = {
    ("OCASregion", "smrBuilding", "smrDisused", "smrRunway", "smrTaxiway", "blackBackground") : "Black",
    ("smrHHcompass",) : "smrCompassbase",
    ("smrGDtaxiway", "smrJJtaxiway", "smrSCOTaxiway", "smrMilTaxiway") : "smrTaxiwayDarker",
    ("smrGDrunway", "smrGrey", "smrSCORunway") : "smrGrey",
    ("smrMilRoad",) : "smrRoad",
    ("smrBlue", "blueBackground") : "Blue",
    ("smrSCOGrass",) : "smrGreen",
    ("smrPFApron", "smrPFHoldLabels") : "smrPFGreyDark",
    ("smrPFRwyOuter","smrPFStandLabels") : "smrPFGreyLight"

}


flattened_map = {name.lower(): value for keys, value in to_compress.items() for name in keys}


def check() -> None:
    print("Scanning...")
    with open("Colours.txt", "r")as f:
        data = f.read().splitlines()
    colours = {}
    defs = {}

    for d in data:
        if d.startswith("#define"): # is colour
            d = d.split()
            colours[d[1]] = -1
            if d[2] not in defs:
                defs[d[2]] = [d[1]]
            else:
                defs[d[2]].append(d[1])

    with open(".bin/UK.sct","r")as sct:
        data = sct.read().splitlines()
    data = [item for sublist in [d.split(" ") for d in data] for item in sublist]

    for d in data:
        if d in colours:
            colours[d] += 1

    sorted_colours = {k: v for k, v in sorted(colours.items(), key=lambda item: item[1])}
    sorted_defs = {k: v for k, v in sorted(defs.items(), key=lambda item: len(item[1]),reverse=True)}

    with open('colours.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Colour', 'Value'])
        for key, value in sorted_colours.items():
            writer.writerow([key, value])

    with open("defs.csv","w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Colour', 'Names'])
        for key, value in sorted_defs.items():
            writer.writerow([key, value])

    print("Done")

def sort_colours() -> None:                 
    with open("Colours.txt","r")as in_file:
        data = in_file.readlines()
    data.insert(0, ";Misc\n")
    replaced_lines = []
    for line in data:
        if line.startswith("#define"):
            _, col, def_ =  line.split(" ")
            if col.lower() in flattened_map:
                col = flattened_map[col.lower()]
            line = line = " ".join(("#define",col,def_))
        replaced_lines.append(line)
    
    section_pattern = re.compile(r'^;(\S.*$)')
    sections = {}
    current_section = ""
    comments = {}
    for line in replaced_lines:
        match = section_pattern.match(line)
        if match:
            current_section = match.group(0)
            sections[current_section] = []
        else:
            if line.strip().startswith('; @preserveComment'):
                if sections[current_section]:
                    last_line = sections[current_section][-1]
                    comments.setdefault(last_line, []).append(line.strip())
            else:
                sections[current_section].append(line.strip())

    fixed_sections = {
        ";Misc" :set(),
        ";SMR Colours" : set(),
        ";Background Colours" : set()
    }
    for col_defs in sections.values():
        for col in col_defs:
            if col:
                _, name, def_ =  col.split(" ")
                if name.startswith("smr"):
                    fixed_sections[";SMR Colours"].add(" ".join(("#define",name,def_)))
                elif name in ["Black","Blue"]:
                    fixed_sections[";Background Colours"].add(" ".join(("#define",name,def_)))
                else:
                    fixed_sections[";Misc"].add(" ".join(("#define",name,def_)))
    

    sorted_sections = {}
    for section, lines in fixed_sections.items():
        sorted_lines = sorted(lines, key=lambda x: x.lower())
        sorted_sections[section] = []
        for line in sorted_lines:
            sorted_sections[section].append(line)
            if line in comments:
                sorted_sections[section].extend(comments[line])


    
    with open("Colours.txt", "w") as file:
        for i,section in enumerate(sorted_sections):
            if i != 0:
                file.write(f"\n{section}\n")
            for line in sorted_sections[section]:
                if line != "":
                    file.write(f"{line}\n")
        
def remove_unused() -> None:
    check()
    to_remove = set() # not used colours
    with open("colours.csv","r")as file:
        csv_reader = csv.reader(file)
        _ = next(csv_reader)
        for row in csv_reader:
            if int(row[1]) == 0:
                to_remove.add(row[0])

    with open("Colours.txt", "r")as f:
        data = f.read().splitlines()

    with open("Colours.txt","w")as out_file:
        for line in data:
            if line.startswith("#define"): # colour
                line_split = line.split(" ")
                if line_split[1] not in to_remove:
                    out_file.write(f"{line}\n")
            else:
                out_file.write(f"{line}\n")

def compress_colours() -> None:
    prev_line = ""

    print("Processing Airports")
    for root,dirs,_ in os.walk("Airports"):
        if "SMR" in dirs:
            path = os.path.join(root,"SMR")
            for smr_file in os.listdir(path):
                file_path = os.path.join(path, smr_file)
                if os.path.isfile(file_path):
                    type_ = file_path.split("\\")[-1].split(".")[0]
                    with open(file_path,"r")as in_file:
                        data = in_file.read().splitlines()
                    with open(file_path,"w")as out_file:
                        for line in data:
                            if type_ == "Geo" or type_ == "Labels":
                               if not line.startswith(";") and line != "":
                                content ,_ ,_ = line.partition(";")
                                colour = content.split()[-1]
                                if colour.lower() in flattened_map:
                                    line = line.replace(colour,flattened_map[colour.lower()])
                            elif type_ == "Regions":
                                if prev_line.startswith("REGIONNAME"):
                                    colour = line.split(" ")[0]
                                    if colour.lower() in flattened_map:
                                        line = line.replace(colour, flattened_map[colour.lower()])
                                prev_line = line

                            out_file.write(f"{line}\n")

    print("Processing Closed Airfields")
    for root,dirs,_ in os.walk("_data\Closed Airfields"):
        if "Ground Map" in dirs:
            path = os.path.join(root,"Ground Map")
            for smr_file in os.listdir(path):
                file_path = os.path.join(path, smr_file)
                if os.path.isfile(file_path):
                    type_ = file_path.split("\\")[-1].split(".")[0]
                    with open(file_path,"r")as in_file:
                        data = in_file.read().splitlines()
                    with open(file_path,"w")as out_file:
                        for line in data:
                            if type_ == "Geo" or type_ == "Labels":
                                if not line.startswith(";") and line != "":
                                    content ,_ ,_ = line.partition(";")
                                    colour = content.split()[-1]
                                    if colour.lower() in flattened_map:
                                        line = line.replace(colour,flattened_map[colour.lower()])
                            elif type_ == "Regions":
                                if prev_line.startswith("REGIONNAME"):
                                    colour = line.split(" ")[0]
                                    if colour.lower() in flattened_map:
                                        line = line.replace(colour, flattened_map[colour.lower()])
                                prev_line = line

                            out_file.write(f"{line}\n")
    
    print("Processing Misc")
    for path in glob.glob(os.path.join("Misc Geo", "*txt")):
        with open(path,"r")as in_file:
            data = in_file.read().splitlines()
        with open(path, "w")as out_file:
            for line in data:
                if not line.startswith(";") and line != "":
                    content ,_ ,_ = line.partition(";")
                    colour = content.split()[-1]
                    if colour.lower() in flattened_map:
                        line = line.replace(colour,flattened_map[colour.lower()])
                out_file.write(f"{line}\n")

    for path in glob.glob(os.path.join("Misc Other", "*txt")):
        with open(path,"r")as in_file:
            data = in_file.read().splitlines()
        with open(path, "w")as out_file:
            for line in data:
                if not line.startswith(";") and line != "":
                    content ,_ ,_ = line.partition(";")
                    colour = content.split()[-1]
                    if colour.lower() in flattened_map:
                        line = line.replace(colour,flattened_map[colour.lower()])
                out_file.write(f"{line}\n")

    for path in glob.glob(os.path.join("Misc Regions", "*txt")):
        with open(path,"r")as in_file:
            data = in_file.read().splitlines()
        with open(path, "w")as out_file:
            for line in data:
                if prev_line.startswith("REGIONNAME"):
                    colour = line.split()[0]
                    if colour.lower() in flattened_map:
                        line = line.replace(colour, flattened_map[colour.lower()])
                prev_line = line

                out_file.write(f"{line}\n")
    
    print("Colours Merged")

def remove_blank_ends() -> None:

    for root,dirs,_ in os.walk("Airports"):
        if "SMR" in dirs:
            smr_path = os.path.join(root,"SMR")
            for smr_file in os.listdir(smr_path):
                file_path = os.path.join(smr_path, smr_file)
                if os.path.isfile(file_path):
                    with open(file_path,"r")as file:
                        lines = file.readlines()
                    while lines and lines[-1].strip() == "":
                        lines.pop()
                    with open(file_path,"w")as file:
                        file.writelines(lines)


    for root,dirs,_ in os.walk("_data\Closed Airfields"):
        if "Ground Map" in dirs:
            smr_path = os.path.join(root,"Ground Map")
            for smr_file in os.listdir(smr_path):
                file_path = os.path.join(smr_path, smr_file)
                if os.path.isfile(file_path):
                    with open(file_path,"r")as file:
                        lines = file.readlines()
                    while lines and lines[-1].strip() == "":
                        lines.pop()
                    with open(file_path,"w")as file:
                        file.writelines(lines)

    for path in glob.glob(os.path.join("Misc Geo","*txt")):
        with open(path,"r")as file:
            lines = file.readlines()
        while lines and lines[-1].strip() == "":
            lines.pop()
        with open(path,"w")as file:
            file.writelines(lines)

    for path in glob.glob(os.path.join("Misc Other","*txt")):
        with open(path,"r")as file:
            lines = file.readlines()
        while lines and lines[-1].strip() == "":
            lines.pop()
        with open(path,"w")as file:
            file.writelines(lines)

    for path in glob.glob(os.path.join("Misc Regions","*txt")):
        with open(path,"r")as file:
            lines = file.readlines()
        while lines and lines[-1].strip() == "":
            lines.pop()
        with open(path,"w")as file:
            file.writelines(lines)



    print("Removed Blank Ends")

def are_colours_close(col1 : int, col2: int, threshold : int = 30) -> bool:
    rgb1 = conv_rgb(col1)
    rgb2 = conv_rgb(col2)
    return sum((a-b) ** 2 for a,b in zip(rgb1,rgb2))** 0.5 <= threshold

def compile_sf() -> bool:
    command = r" .\cli-windows-x64.exe --config-file ./compiler.config.json --no-wait"
    process = subprocess.run(command,shell=True)
    if process.returncode == 0:
        print("SF compiled Succesfully")
        return 1
    else:
        print("There was an error")
        return 0

def close_colours() -> None:
    close = []
    with open("Colours.txt","r")as file:
        data = file.read().splitlines()
    colours = [line[-1] for line in data if line.startswith("#define")]
    for i,colour1 in enumerate(colours):
        for colour2 in colours[i+1:]:
            if are_colours_close(colour1,colour2):
                close.append((colour1,colour2))

    with open("colse_colours.txt","w")as file:
        for pair in close:
            file.write(f"{pair}\n")


if __name__ == "__main__":
    remove_unused()
    compress_colours()
    sort_colours()
    remove_blank_ends()
    sf_check = compile_sf()
    check()
    close_colours()
    print("Completed")