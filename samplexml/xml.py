import os
import uuid
from datetime import datetime
from unidecode import unidecode
import logging
from tp.check_patient import check_patient_data
import openpyxl
from openpyxl import Workbook
from logging_excel.log import log_message_to_excel

logger = logging.getLogger(__name__)

def xml_create(config, region_combobox, local_uid_text, root, progress_callback=None, mpi_mismatch_errors=True):
   """
    Генерирует XML-файлы для пациентов на основе конфигурации и данных.

    Выбирает регион из конфигурации и создает XML-файлы для каждого локального UID из текста. Файлы сохраняются 
    в папку `work`. В случае успешного создания XML файла результат добавляется в Excel-лог. При ошибках 
    запись добавляется в лог и файл не создается.

    :param config: Конфигурационный файл с настройками.
    :param region_combobox: Виджет для выбора региона.
    :param local_uid_text: Виджет с текстом, содержащим локальные UID.
    :param root: Корневой элемент для обработки данных.
    :param progress_callback: Функция обратного вызова для отслеживания прогресса (необязательно).
    :param mpi_mismatch_errors: Учитывать ли ошибки PATIENT_MPI_MISMATCH при валидации (по умолчанию True).
    :return: Список локальных UID, для которых возникли ошибки.
   """
   logger.info("Начало выполнения функции xml_create")
   try:
      selected_region = region_combobox.get()
      selected_region_config = config["regions"][selected_region]
      region_id = selected_region_config.get("region_id")

      logger.info(f"Выбранный регион: {selected_region}")

      current_directory = os.getcwd()
      outdata_directory = os.path.join(current_directory, 'work')
      if not os.path.exists(outdata_directory):
            os.makedirs(outdata_directory)


      local_uids = local_uid_text.get("1.0", "end-1c").strip().split('\n')
      total_uids = len(local_uids)
      error_local_uids = []
      successful_count = 0
      
      for index, local_uid in enumerate(local_uids, start=1):
         if local_uid.strip():   
            logger.info(f"Локальный UID: {local_uid}")
            if result:= check_patient_data(f"data/{local_uid}.json", root, mpi_mismatch_errors):

               logger.info(f"Проверенные данные пациента: {result}")

               current_datetime = datetime.now()
               formatted_datetime = current_datetime.strftime("%Y%m%d%H%M%S")

               XML = f"""<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:urn="urn:hl7-org:v3" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
         <soap:Header>
            <transportHeader wsu:Id="Id-8D835103-150B-4736-8351-03150B673691" xmlns="http://egisz.rosminzdrav.ru">
               <authInfo>
               <!--Идентификатор РМИС, ниже указан для хмао, для других регионов менять соотвественно-->
                  <clientEntityId>{region_id}</clientEntityId>
               </authInfo>
            </transportHeader>
            <!--менять все гуиды начиная с этого-->
            <a:Action wsu:Id="Id-{uuid.uuid4()}">urn:hl7-org:v3:PRPA_IN201302</a:Action>
            <a:MessageID wsu:Id="Id-{uuid.uuid4()}">urn:uuid:{uuid.uuid4()}</a:MessageID>
            <a:ReplyTo wsu:Id="Id-{uuid.uuid4()}">
               <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
            </a:ReplyTo>
            <!--Адрес конечной точки, куда отправляется данное сообщение, указан прод-->
            <a:To wsu:Id="Id-{uuid.uuid4()}">https://ips.rosminzdrav.ru/52dd1bfaca6c5</a:To>
         </soap:Header>
         <soap:Body wsu:Id="BodyId-{uuid.uuid4()}">
            <PRPA_IN201302RU02 ITSVersion="XML_1.0" xsi:schemaLocation="urn:hl7-org:v3 ../../../../../../iemk-integration/iemk-integration-ws-api/src/main/resources/integration/schema/HL7V3/NE2008/multicacheschemas/PRPA_IN201302RU02.xsd" xmlns="urn:hl7-org:v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <!--заканчивая этим ниже-->      
            <id extension="{result['localId']}" root="{result['organizationCode']}"/>
      <!--указать текущие датувремя в формате ггггммддччммсс-->      
               <creationTime value="{formatted_datetime}"/>
               <interactionId extension="PRPA_IN201302RU02" root="1.2.643.5.1.13.2.7.3"/>
               <processingCode code="P"/>
               <processingModeCode code="T"/>
               <acceptAckCode code="AL"/>
               <receiver typeCode="RCV">
                  <device classCode="DEV" determinerCode="INSTANCE">
                     <id root="d5a0f9c0-5db4-11e3-949a-0800200c9a66"/>
                     <name>ИЭМК</name>
                     <asAgent classCode="ASSIGNED">
                        <representedOrganization classCode="ORG" determinerCode="INSTANCE">
                           <id root="1.2.643.5.1.13"/>
                           <name>МЗ РФ</name>
                        </representedOrganization>
                     </asAgent>
                  </device>
               </receiver>
               <sender typeCode="SND">
                  <device classCode="DEV" determinerCode="INSTANCE">
                     <id root="143423de-69bf-40dd-852e-3b8e22e26492"/>
                     <name>MEDVED</name>
                     <asAgent classCode="ASSIGNED">
                        <representedOrganization classCode="ORG" determinerCode="INSTANCE">
                        <!--указать оид, который выяснили скриптом-->      
                           <id root="{result['organizationCode']}"/>
                           <!--указать наименование мо, которое выяснили скриптом-->      
                           <name>{result['organizationDisplayName']}</name>
                        </representedOrganization>
                     </asAgent>
                  </device>
               </sender>
               <controlActProcess classCode="CACT" moodCode="EVN">
                  <subject typeCode="SUBJ">
                     <registrationEvent classCode="REG" moodCode="EVN">
                        <id nullFlavor="NA"/>
                        <statusCode code="active"/>
                        <subject1 typeCode="SBJ">
                           <patient classCode="PAT">
                           <!--значение extension - указать снилс пациента, root - оид мо  -->      
                              <id extension="{result['localId']}" root="{result['organizationCode']}"/>
                              <statusCode code="active"/>
                              <patientPerson>
                                 <name>
                                 <!--фио пациента-->      
                                    <family>{result['surname']}</family>
                                    <given>{result['name']}</given>
                                    <given>{result['patrName']}</given>
                                 </name>
                                 <telecom value="mailto:qwerty@mail.ru"/>
                                 <!--пол пациента-->
                                 <administrativeGenderCode code="{result['gender']}" codeSystem="1.2.643.5.1.13.2.1.1.156"/>
                                 <!--др пациента-->
                                 <birthTime value="{result['birthDate'].replace("-", "")}"/>
                                 <!--СНИЛС указываем тот, который был предоставлен пользователем-->
                                 <asOtherIDs classCode="IDENT">
                                    <documentType code="3" codeSystem="1.2.643.5.1.13.2.7.1.62"/>
                                    <documentNumber number="{result['snils']}"/>
                                    <scopingOrganization classCode="ORG" determinerCode="INSTANCE">
                                       <id nullFlavor="NI"/>
                                    </scopingOrganization>
                                 </asOtherIDs>						   
                              </patientPerson>
                              <providerOrganization classCode="ORG" determinerCode="INSTANCE">
                              <!--указать оид, который выяснили скриптом-->      
                                 <id root="{result['organizationCode']}"/>
                                 <!--указать наименование мо, которое выяснили скриптом-->
                                 <name>{result['organizationDisplayName']}</name>
                                 <contactParty classCode="CON">
                                    <telecom value="tel:+7-987-456-123"/>
                                 </contactParty>
                              </providerOrganization>
                           </patient>
                        </subject1>
                        <custodian typeCode="CST">
                           <assignedEntity classCode="ASSIGNED">
                           <!--указать оид, который выяснили скриптом-->      
                              <id root="{result['organizationCode']}"/>
                              <assignedOrganization classCode="ORG" determinerCode="INSTANCE">
                              <!--указать наименование мо, которое выяснили скриптом-->
                                 <name>{result['organizationDisplayName']}</name>
                              </assignedOrganization>
                           </assignedEntity>
                        </custodian>
                     </registrationEvent>
                  </subject>
               </controlActProcess>
            </PRPA_IN201302RU02>
         </soap:Body>
      </soap:Envelope>"""
               
               
               patr_name = result.get('patrName', "")
               first_char = patr_name[0] if patr_name else ""

               complete_name = os.path.join(outdata_directory, f"{unidecode(result.get('surname', f'{local_uid}')+result.get('name', "")[0]+first_char, 'ru').replace(" ", '-').replace("'", "")}.xml")
               
               
               try:
                  with open(complete_name, "w", encoding="utf-8") as file:
                     file.write(XML)
                     logger.info(f"Сгенерирован XML: {unidecode(result.get('surname', f'{local_uid}')+result.get('name', "")[0]+first_char, 'ru').replace(" ", '-').replace("'", "")}.xml")
                     successful_count += 1
               except Exception as e:
                     logger.error("Ошибка генерации XML: %s" % e)
                     log_message_to_excel('Странно', [(local_uid, f"XML не сгенерирован хотя прошел проверку {unidecode(result.get('surname', f'{local_uid}')+result.get('name', "")[0]+first_char, 'ru').replace(" ", '-').replace("'", "")}.xml")])

               logger.info("Создание XML завершено")
            else:
               error_local_uids.append(local_uid)

               if progress_callback:
                    progress_callback(index, total_uids)

      return error_local_uids
   
   except Exception as e:
      logger.error(f"Ошибка в функции xml_create: {e}")
      return []


