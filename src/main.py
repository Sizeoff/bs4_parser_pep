import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, EXPECTED_STATUS, PYTHON3_DOC_URL
from outputs import control_output
from utils import get_response, find_tag


def pep(session):
    results = [('Статус', 'Количество')]

    response = session.get(MAIN_DOC_URL)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    section = find_tag(soup, 'section', {'id': 'numerical-index'})
    table = section.find('table',
                         {'class': 'pep-zero-table docutils align-default'})
    body = table.find('tbody')
    rows = body.find_all('tr')

    for el in tqdm(rows):
        statuses_common = el.find('abbr')['title'].split(', ')
        object = el.find('a', {'class': 'pep reference internal'})
        link = object['href']
        pep_private_url = urljoin(MAIN_DOC_URL, link)

        response = session.get(pep_private_url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        statuses_private = soup.find(
            'abbr').text

        if len(statuses_common) == 2 and (
                statuses_common[1] != statuses_private):
            logging.error(f'''Несовпадающие статусы:
                                {pep_private_url}
                                Статус в карточке: {statuses_private}
                                Статус в списке: {statuses_common[1]}''')

        if statuses_private[0] in EXPECTED_STATUS.keys():
            EXPECTED_STATUS[statuses_private[0]] += 1
        else:
            logging.error(f'Незапланированный статус: "{statuses_private[0]}"')
    results.extend(list(EXPECTED_STATUS.items()))

    return results


def whats_new(session):
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]

    whats_new_url = urljoin(PYTHON3_DOC_URL, 'whatsnew/')

    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')

    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})

    div_with_ul = main_div.find('div', attrs={'class': 'toctree-wrapper'})

    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})

    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = soup.find('h1')
        dl = soup.find('dl')
        dl_text = dl.text.replace('\n', ' ')

        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    results = [('Ссылка на документацию', 'Версия', 'Статус')]

    response = get_response(session, PYTHON3_DOC_URL)
    if response is None:
        return
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Не найден список c версиями Python')

    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:

        link = a_tag['href']

        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:

            version, status = text_match.groups()
        else:

            version, status = a_tag.text, ''

        results.append(
            (link, version, status)
        )

    return results


def download(session):
    downloads_url = urljoin(PYTHON3_DOC_URL, 'download.html')
    response = session.get(downloads_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    main_tag = find_tag(soup, 'div', {'role': 'main'})
    table_tag = main_tag.find('table', {'class': 'docutils'})
    pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(PYTHON3_DOC_URL, pdf_a4_link)
    filename = archive_url.split('/')[-1]

    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    response = get_response(session, downloads_url)
    if response is None:
        return

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())

    args = arg_parser.parse_args()

    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()

    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode

    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
