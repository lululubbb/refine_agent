package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_1Test {

    @Test
    public void testGet_withValidHeader_returnsValue() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header1");

        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_withNullMapping_throwsIllegalStateException() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        Exception exception = Assertions.assertThrows(IllegalStateException.class, () -> {
            record.get("header1");
        });

        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getMessage());
    }

    @Test
    public void testGet_withInvalidHeader_returnsNull() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header2");

        Assertions.assertNull(result);
    }

    @Test
    public void testGet_withOutOfBoundsIndex_throwsIllegalArgumentException() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1); // Correct index
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Exception exception = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGet(record, "header2"); // This should not throw an exception
        });

        Assertions.assertTrue(exception.getMessage().contains("Index for header 'header2' is 1 but CSVRecord only has 2 values!"));
    }

    private String invokeGet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, name);
    }
}