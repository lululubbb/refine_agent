package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_2Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        mapping.put("name", 0);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet("name");
        
        Assertions.assertTrue(result);
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        mapping.put("name", 2);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet("name");
        
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet("name");
        
        Assertions.assertFalse(result);
    }

    private boolean invokeIsSet(String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(csvRecord, name);
    }
}