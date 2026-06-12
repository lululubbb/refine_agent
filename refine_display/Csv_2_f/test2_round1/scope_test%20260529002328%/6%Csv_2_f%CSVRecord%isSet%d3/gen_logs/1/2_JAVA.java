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

public class CSVRecord_6_1Test {

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertTrue(result);
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 1);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertFalse(result);
    }

    private boolean invokeIsSet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        return (Boolean) method.invoke(record, name);
    }
}