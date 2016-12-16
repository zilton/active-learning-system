# coding: utf-8 -*-

context={"1000" : {}}
c=context["1000"]

c["reader"]={"*" : {"*" : "lang"}}

c["classifier"]={"*" : "select_instance"}

c["update"]={"*" : {"*" : "#END#"}}

c["lang"]={"*" : {"pt" : "classifier", "*" : "#END#"}}

c["select_instance"]={"*" : {"*":"update"}}
