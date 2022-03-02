-----------------------------------------------------------------------------------------------
This README file describes how to generate Section 5 of the CTF Software Design Document (SDD).
-----------------------------------------------------------------------------------------------

All the official CTF documents are in PDF format in this directory. If the users want to re-geneate
the section 5 of the CTF Software Design Document (SDD), CTF_sdd_s5.pdf, follow the instructions
below from this directory.

1. To generate only the PDF files,

       $ ./build_dox.sh pdf        /* for CTF_sdd_s5.pdf */
       $ ./build_dox.sh nasa_pdf   /* for CTF_sdd_s5-nasa.pdf - NASA version */

2. To generate only the HTML files, 

       $ ./build_dox.sh html         /* for CTF_sdd_s5 */
       $ ./build_dox.sh nasa_html    /* for CTF_sdd_s5-NASA - NASA version */

3. To generate both the HTML and PDF files,

       $ ./build_dox.sh all
       $ ./build_dox.sh nasa_all

4. To view the PDF files on Linux,

       $ evince ./CTF_sdd_s5.pdf 
       $ evince ./CTF_sdd_s5-nasa.pdf 

5. To view the HTML files on Linux,

       $ firefox html/index.html 

6. To remove the untracked, doxygen-generated files,

       $ ./build_dox.sh clean
