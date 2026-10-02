create music organizer, start with with planning spec and implementation spec, with dedicated prompts files. #file:./music_organizer.py
1. go through music files (one each at time), get metadata information
2. clean metadata information, remove noise words, add some rules, like album will not have year. 
3. Insert cleaned metadata back into the music file, and save it.
4. Create a user interface to display the music files and their metadata, allowing users to edit and update the information as needed.
5. ensure music files are not corrupted during the process, and provide error handling for any issues that arise.
6. Implement a search and filter functionality in the user interface to allow users to easily find specific music files based on metadata attributes.
7. Create a separate process where metadata information is not there, to read information from CLI or using json in same format as metadata, and insert it into the music file.
8. Default file name - album - title.
9. Create a report of the changes made to the music files with metadata information, including any errors encountered during the process. How to validate this report?
10. Add directory structure, music/ip and music/op and music/nc, ip=input, op=output, nc=nochange
11. Seperate process where metadata information is not there has to read files from music/nc.
12. dry run in default with report generation, and --apply will apply.
13. Create some test cases to validate the functionality of the music organizer, including edge cases and error scenarios.
