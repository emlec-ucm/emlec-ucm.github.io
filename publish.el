(require 'ox-publish)

(use-package htmlize)

;; Customize the HTML output
(setq org-html-validation-link nil            ;; Don't show validation link
      org-html-head-include-scripts nil       ;; Use our own scripts
      org-html-head-include-default-style nil ;; Use our own styles
      org-html-head "<link rel=\"stylesheet\" href=\"https://cdn.simplecss.org/simple.min.css\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<meta charset=\"UTF-8\">")

(let* ((base-directory "./")
       (org-export-with-broken-links t)
       (org-publish-project-alist `(("html"
				     :base-directory ,(concat base-directory "content")
				     :base-extension "org"
				     :publishing-directory ,(concat base-directory "docs")
				     :exclude "docs"
				     :recursive t
				     :publishing-function org-html-publish-to-html
				     :auto-preamble t
				     :auto-sitemap t
                                     :with-author nil           ;; Don't include author name
                                     :with-creator nil          ;; Include Emacs and Org versions in footer
                                     :with-toc t                ;; Include a table of contents
                                     :section-numbers nil       ;; Don't include section numbers
                                     :time-stamp-file nil)
				    
				    ("static-html"
				     :base-directory ,(concat base-directory "content")
				     :base-extension "css\\|js\\|png\\|jpg\\|gif\\|pdf\\|dat\\|mov\\|txt\\|svg\\|aiff\\|xml\\|html"
				     :publishing-directory ,(concat base-directory "docs")
				     :exclude "docs"
				     :recursive t
				     :publishing-function org-publish-attachment)

				    ("static-root"
				     :base-directory ,base-directory
				     :base-extension "txt"
				     :publishing-directory ,(concat base-directory "docs")
				     :exclude "docs\\|content\\|css\\|scripts\\|requirements\\|.git"
				     :recursive nil
				     :publishing-function org-publish-attachment)

				    ;; ... all the components ...
				    ;("scimax-eln" :components ("html" "static-html" "pdf")))))
				    ("web-grupo" :components ("html" "static-html" "static-root")))))

  (org-publish "web-grupo" t))
