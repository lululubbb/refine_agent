package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_2Test {

    @Test
    public void testisMapped_mappingIsNotNullAndContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value"}, mapping, null, 1);
        
        boolean result = invokeIsMapped(record, "name");
        
        Assertions.assertTrue(result);
    }

    @Test
    public void testisMapped_mappingIsNotNullAndDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value"}, mapping, null, 1);
        
        boolean result = invokeIsMapped(record, "unknown");
        
        Assertions.assertFalse(result);
    }

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value"}, null, null, 1);
        
        boolean result = invokeIsMapped(record, "name");
        
        Assertions.assertFalse(result);
    }

    private boolean invokeIsMapped(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(record, name);
    }
}