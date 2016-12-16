package br.org.inweb.ctweb.lac.mbean;

import javax.management.MBeanAttributeInfo;
import javax.management.MBeanConstructorInfo;
import javax.management.MBeanInfo;
import javax.management.MBeanNotificationInfo;
import javax.management.MBeanOperationInfo;
import javax.management.MBeanParameterInfo;
import javax.management.StandardMBean;

import br.org.inweb.ctweb.lac.server.Lac;

public class LacMBeanImpl extends StandardMBean implements LacMBean {
	private Lac lac;
	public LacMBeanImpl(Lac lac) {
		super(LacMBean.class, false);
		this.lac = lac;
	}

	@Override
	public void load(int maxRuleSize, double minSupport, double minConfidence,
			boolean considerFeaturePosition, String trainName, String trainPath) {
		try {
			lac.construirClassificador(maxRuleSize, minSupport, minConfidence,
				considerFeaturePosition, trainName, trainPath);
		} catch(Exception e){
			throw new RuntimeException(e.getMessage());
		}
	}

	@Override
	public String getTrainsName() {
		StringBuilder result = new StringBuilder();
		for (String name : lac.getTrainsName()) {
			result.append(name).append(", ");
		}
		if (result.length() > 0){
			result.setLength(result.length() - 2);
		}
		return result.toString();
	}

	@Override
	public void remove(String trainName) {
		try{
			lac.remove(trainName);
		} catch(Exception e){
			throw new RuntimeException(e.getMessage());
		}
	}
	@Override
	public MBeanInfo getMBeanInfo() {
		MBeanAttributeInfo[] attrInfo = new MBeanAttributeInfo[]{
			new MBeanAttributeInfo("TrainsName", "java.lang.String", "Retorna a lista de treinos", true, true, false)
		};
		MBeanOperationInfo[] opInfo = new MBeanOperationInfo[]{
			new MBeanOperationInfo("load",
				"Carrega um arquivo de treino",
				new MBeanParameterInfo[]{
					new MBeanParameterInfo("maxRuleSize", "int", "Tamanho máximo das regras (parâmetro -n)"),
					new MBeanParameterInfo("minSupport", "double", "Suporte mínimo (parâmetro -s)"),
					new MBeanParameterInfo("minConfidence", "double", "Confiança mínima (parâmetro -c)"),
					new MBeanParameterInfo("considerFeaturePosition", "boolean", ""),
					new MBeanParameterInfo("trainName", "java.lang.String", "Nome do treino (seleciona qual treino aplicar ao teste)"),
					new MBeanParameterInfo("trainPath", "java.lang.String", "Caminho completo para o arquivo com o treino")
				},
				"void",
				MBeanOperationInfo.ACTION),
			new MBeanOperationInfo("remove",
					"Remove um treino do servidor",
					new MBeanParameterInfo[]{
						new MBeanParameterInfo("trainName", "java.lang.String", "Nome do treino a ser removido"),
					},
					"void",
					MBeanOperationInfo.ACTION)
		};
		MBeanInfo info = new MBeanInfo(this.getClass().getCanonicalName(), 
				"Operações relacionadas ao LAC Server", 
				attrInfo, 
				new MBeanConstructorInfo[]{}, 
				opInfo, 
				new MBeanNotificationInfo[]{});
		return info;
	}
}
