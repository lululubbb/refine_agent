package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_5Test {

    @Test
    public void testisMapped_mappingIsNotNullAndContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key1");

        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisMapped_mappingIsNotNullAndDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key2");

        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisMapped_mappingIsNull() throws Exception {
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, null, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key1");

        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key1");

        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisMapped_nullKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, null);

        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisMapped_keyWithEmptyString() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "");

        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisMapped_keyWithSpecialCharacters() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key@#1", 1);
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);

        boolean result = invokeIsMapped(csvRecord, "key@#1");

        Assertions.assertEquals(true, result);
    }

    private boolean invokeIsMapped(CSVRecord csvRecord, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(csvRecord, name);
    }
}