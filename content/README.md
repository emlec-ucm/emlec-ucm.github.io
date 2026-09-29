- [Carpeta con ficheros fuente de las distintas páginas de esta web](#org48deea0)


<a id="org48deea0"></a>

# Carpeta con ficheros fuente de las distintas páginas de esta web

Están en formato `org-mode` y se exportan a `html` con [GNU Emacs](https://www.gnu.org/software/emacs/) ejecutando el guión [`publish.el`](file:///home/marcos/CloudStation/ReposGH/PaginaWeb/emlec-ucm.github.io/publish.el) del siguiente modo:

```bash
emacs --batch -l publish.el
```

(también se pueden exportar con [Pandoc](https://pandoc.org/)).

Los ficheros `html` generados a partir de los ficheros fuente `.org` se situan en la carpeta [`docs`](file:///home/marcos/CloudStation/ReposGH/PaginaWeb/emlec-ucm.github.io/docs/) (de la rama `gh-pages`). Es ese directorio el que nutre la [web](https://emlec-ucm.github.io/) mediante [GitHub pages](https://pages.github.com/).

Para todo esto me he basado en <https://github.com/jkitchin/scimax-eln?tab=readme-ov-file>. Los pasos del *workflow* que exporta los ficheros a `html` y los copia en la carpeta [`docs`](file:///home/marcos/CloudStation/ReposGH/PaginaWeb/emlec-ucm.github.io/docs/) (de la rama `gh-pages`) se pueden ver en el fichero [publish.yml](file:///home/marcos/CloudStation/ReposGH/PaginaWeb/emlec-ucm.github.io/.github/workflows/publish.yml).
