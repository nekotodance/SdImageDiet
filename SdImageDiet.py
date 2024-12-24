import os
from concurrent.futures import ThreadPoolExecutor
import shutil
import sdfileUtility

def convert_imgfile(infile, outfile, imgtype, quality, keeptimestamp):
    sdfileUtility.convert_image(infile, outfile, imgtype, quality)
    if keeptimestamp:
        shutil.copystat(infile, outfile)

def convert_imgfiles(infile, outdir, imgtype, quality, keeptimestamp):
    fn, ext = os.path.splitext(os.path.basename(infile))
    outfile = f"{outdir}/{fn}{imgtype}"
    convert_imgfile(infile, outfile, imgtype, quality, keeptimestamp)

def process_files(input, output, imgtype, quality, keeptimestamp, max_workers):
    fn, ext = os.path.splitext(output)
    if not ext:
        # output is dir
        output = output.rstrip(os.sep)
        if not os.path.exists(output):
            os.makedirs(output)
    elif ext in (".jpg", ".webp"):
        #output is file. file extension takes precedence
        imgtype = ext
        if os.path.isdir(input):
            print("Error : If a file is specified for output, the input must also be a file.")
            return
        convert_imgfile(input, output, imgtype, quality, keeptimestamp)
        return
    in_files = []
    if os.path.isfile(input):
        in_files = [input] if input.lower().endswith(('.png', '.jpg', '.webp')) else []
    elif os.path.isdir(input):
        # Check output files for duplicates
        duplicatefile = check_duplicate_file_in_folder(input, None)
        if duplicatefile:
            print("Error : Duplicate output files. {duplicatefile}")
            return

        for root, _, files in os.walk(input):
            in_files.extend([os.path.join(root, f) for f in files if f.lower().endswith(('.png', '.jpg', '.webp'))])

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(convert_imgfiles, img_file, output, imgtype, quality, keeptimestamp) for img_file in in_files]
        for future in futures:
            future.result()

#重複がなければNone、あれば重複したファイル名を返却する（単体フォルダ版）
def check_duplicate_file_in_folder(folder_path, outputfolder):
    # フォルダ内の全ての画像ファイルを再帰的に取得
    img_files = []
    # Output folders are not covered.
    if os.path.basename(os.path.normpath(folder_path)) == outputfolder:
        return None
    for root, dirs, files in os.walk(folder_path):
        # Output folders are not covered.
        if os.path.basename(os.path.normpath(root)) == outputfolder:
            continue
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.webp')):
                filename = os.path.splitext(root + "/" + file)[0]
                if filename in img_files:
                    return filename # duplicate
                img_files.append(filename)
    return None # not duplicate

#重複がなければNone、あれば重複したファイル名を返却する（複数ファイル、フォルダ版）
def check_duplicate_file(input_paths, outputfolder):
    all_files = []
    for path in input_paths:
        if os.path.isdir(path):  # フォルダの場合
            filename = check_duplicate_file_in_folder(path, outputfolder)
            if filename:
                return filename # duplicate
        elif path.lower().endswith(('.png', '.jpg', '.webp')):  # 対象画像ファイルの場合
            filename = os.path.splitext(path)[0]
            if filename in all_files:
                return filename # duplicate
            all_files.append(filename)
    return None # not duplicate

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert PNG to JPG with metadata.")
    parser.add_argument("input", type=str, help="Input file or directory containing Image files. (png, webp, jpg)")
    parser.add_argument("output", type=str, help="Output file or Output directory")
    parser.add_argument("--imgtype", type=str, default="jpg", help="Image type. def:jpg, webp. If output is a file specification, the file extension takes precedence.")
    parser.add_argument("--quality", type=int, default=85, help="quality (1-100). Default is 85.")
    parser.add_argument("--threads", type=int, default=os.cpu_count() - 1, help="Number of threads for parallel processing. Default is CPU Max Thread - 1.")
    parser.add_argument("--keeptimestamp", action="store_true", help="keep the original timestamp of input files.")

    args = parser.parse_args()
    quality = args.quality
    imgtype = args.imgtype
    threads = args.threads
    if quality < 1 or quality > 100:
        quality = 85
        print(f"Warning : JPEG quality (1-100). Runs at the default value of 85.")
    if threads > os.cpu_count():
        threads = os.cpu_count() - 1
        print(f"Warning : The maximum number of threads on the CPU has been exceeded.")
    if threads < 1:
        threads = 1
        print(f"Warning : Runs with a minimum of 1 thread.")
    if not imgtype in ("jpg", "webp"):
        print(f"not fupport imgtype: {imgtype}.")
        exit()
    imgtype = f".{imgtype}"
    process_files(args.input, args.output, imgtype, quality, args.keeptimestamp, threads)

if __name__ == "__main__":
    main()
