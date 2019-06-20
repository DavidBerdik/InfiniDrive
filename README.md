# ∞ InfiniDrive ∞
```
            ,,,                         ,,,
      &@@@@@@@@@@@@@              @@@@@@@@@@@@@@
    @@@@@@@#    %@@@@@#        @@@@@@@@@@@@@@@@@@@@
  @@@@@@            #@@@     &@@@@@@@         @@@@@@
 @@@@@                @@@@  @@@@@@@             @@@@@
 @@@@                   @@@@@@@@@                @@@@@
@@@@@                    @@@@@@@                  @@@@
@@@@@                    @@@@@@                   @@@@#
@@@@@                   @@@@@@                    @@@@,
&@@@@                 &@@@@@@@@                  *@@@@
 @@@@@               @@@@@@@ @@@                 @@@@@
  @@@@@            *@@@@@@#   @@@               @@@@@
   @@@@@@#       @@@@@@@@      @@@@#          @@@@@@
    *@@@@@@@@@@@@@@@@@@          @@@@@@@@%@@@@@@@@
       #@@@@@@@@@@@@               *@@@@@@@@@@@*
```
InfiniDrive is a project that leverages Google Drive's API and "0 size file" rules for native Docs for unlimited storage space.

Based on a SteelHacks 2019 project by David Berdik, Steven Myrick, and Noah Greenberg

[InfiniDrive Demo Video](https://youtu.be/8u1cwnONJ4E)

## How it Works
InfiniDrive takes advantage of Google Drive's storage policy for Docs stored in Google's native format, which states that native Doc files do not count towards an account's 15GB storage quota. This rule has been previously used to store unlimited data by converting files to base64 strings that are then stored in fragments across as many Docs as necessary. This implementation, although functional, has several disadvantages. Specifically...
- Base64 encodes data to roughly a 4:3 ratio.
- A single Google Doc is limited to one million characters, or approximately 710KB of base64-encoded data.

These limitations mean that very little data can be stored in a single Doc file, which in turn means that performance is decreased since more Drive API interactions are necessary. Drive's API, however, allows for Doc files to be at most 10MB in size (at most 50MB in size when uploaded manually not via the Drive API). Since Google's character limit is much less than 10MB, InfiniDrive achieves close to this size by converting data to images that are stored in Docs. This approach has several advantages over the aforementioned base64 approach because...
- We can store more data per Doc
- Storing more data per Doc means faster processing of data
- Our approach takes advantage of PNG compression meaning that in many cases, the image is smaller than the data it is storing, meaning that we **could** pack more than 9.75MB-worth of the file data per image (more on this later).

## How to Use
1. Clone the InfiniDrive Git repository.
2. Install Python 3. Depending on your Operating System, it may already be installed.
3. Install the Python libraries required by InfiniDrive. If you use pip, you can easily install the required libraries by executing one of the following commands from the root InfiniDrive directory:
    1. `pip install -r requirements.txt`
    2. `python -m pip install -r requirements.txt`
4. Go to the [Google Drive API page](https://developers.google.com/drive/api/v3/quickstart/python) and click on the "Enable the Drive API" button.
5. Complete the API setup, and upon completion, click on the "Download Client Configuration" button.
6. Copy the "credentials.json" file that is downloaded to the root InfiniDrive directory.
7. Run `python InfiniDrive.py` to authenticate your account.
8. After completing authentication, run `python InfiniDrive.py` again to get a list of available commands.

## InfiniDrive Weaknesses
Although InfiniDrive is an improvement over the base64 storage approach, it is certainly not perfect. Here are some of its weaknesses. There are probably more as well. We'll try to keep this list up-to-date if/when new problems arise and old ones are fixed.
- Although InfiniDrive is faster than the base64 implementation, it is still slow. Perhaps this can be improved by moving Drive API interactions to a separate thread since that is the slowest component?
- Google Drive allows for Doc files to be up to 50MB in size, but limits that size to 10MB when uploaded via the API. There used to be a workaround for this. Perhaps an attempt can be made at implementing that workaround?
- As mentioned earlier, taking advantage of PNG compression means that the resulting images are sometimes smaller than the data we are storing. In cases where an image's size is less than the data it is storing, we could pack more data in to the image. InfiniDrive does not currently do this, meaning that we often end up with wasted space per Doc. Perhaps we can try to calculate what an image's size will be before generating it, and add more data to it if the size allows?

## Can I contribute?
Yes! If you are interested in helping build InfiniDrive, feel free to submit a pull request. Bug reports are also appreciated.

## Disclaimer
InfiniDrive was developed as a proof-of-concept project. Although an effort has been made to ensure that any data stored using InfiniDrive will have its integrity maintained, there is no guarantee a lurking edge case did not slip through our testing. By trusting your data's integrity to InfiniDrive, you assume all responsibility if it fails.

--------------------------------------------------

**Please note: InfiniDrive is built and tested with Python 3. Although it may work with Python 2, there are no guarantees and no plans to support it.**

The base64 storage approach, referenced throughout this README, is available at https://github.com/stewartmcgown/uds.

InfiniDrive is based on a [SteelHacks 2019](http://steelhacks.com/) project submission by David Berdik, Steven Myrick, and Noah Greenberg.
[![SteelHacks Logo](/res/steel.png)](http://steelhacks.com/)
