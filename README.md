# foldermon

Python script allowing remote monitoring and access to specified folder via HTTP and a web browser.

![Screen Shot](https://raw.githubusercontent.com/wheresjames/filemon/master/docs/imgs/ss-filemon-md.png)


## Examples:

* Run the python script

`./foldermon/foldermon.py -f /folder/to/server/for/browsing`

* Open in a web browser `http://localhost:8800/`


## Help

```
usage: foldermon.py [-h] [--port PORT] [--html HTML] [--logfile LOGFILE]
                    [--folder FOLDER]

HTTP Server

optional arguments:
  -h, --help            show this help message and exit
  --port PORT, -p PORT  Server Port
  --html HTML, -m HTML  Document root
  --logfile LOGFILE, -l LOGFILE
                        Logfile
  --folder FOLDER, -f FOLDER
                        Folder to monitor
```
