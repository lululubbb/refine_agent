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

public class CSVRecord_5_4Test {

    @Test
    public void testisMapped_keyExists() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(record, "key1");
        Assertions.assertTrue(result);
    }

    @Test
    public void testisMapped_keyDoesNotExist() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(record, "key2");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);

        boolean result = invokeIsMapped(record, "key1");
        Assertions.assertFalse(result);
    }

    private boolean invokeIsMapped(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(record, name);
    }
}