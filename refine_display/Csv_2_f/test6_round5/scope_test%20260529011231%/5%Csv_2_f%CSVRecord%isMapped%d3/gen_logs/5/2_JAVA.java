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

public class CSVRecord_5_5Test {

    @Test
    public void testisMapped_mappingIsNotNullAndContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key1");

        Assertions.assertTrue(result);
    }

    @Test
    public void testisMapped_mappingIsNotNullAndDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key2");

        Assertions.assertFalse(result);
    }

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, null, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key1");

        Assertions.assertFalse(result);
    }

    private boolean invokeIsMapped(CSVRecord csvRecord, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(csvRecord, name);
    }
}