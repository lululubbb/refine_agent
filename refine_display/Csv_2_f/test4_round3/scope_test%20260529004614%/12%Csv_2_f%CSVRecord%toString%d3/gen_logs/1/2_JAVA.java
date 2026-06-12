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

public class CSVRecord_12_1Test {

    @Test
    public void testtoString_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        mapping.put("key3", 2);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 2;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Single value comment";
        long recordNumber = 3;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[singleValue]", result);
    }

    private String invokeToString(CSVRecord csvRecord) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(csvRecord);
    }
}